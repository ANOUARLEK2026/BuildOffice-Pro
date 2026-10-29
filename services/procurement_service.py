# ============================================================
# شرح الملف: services/procurement_service.py
# ============================================================
"""Procurement workflow and purchase-order calculations."""
from __future__ import annotations

import sqlite3

from core.decimal_utils import q2
from core.id_service import next_random_id
from repositories.db import get_connection


def order_totals(items):
    subtotal=discount=tax=0.0
    for x in items:
        qty=max(0,float(x.get("quantity",0))); price=max(0,float(x.get("unit_price",0))); rate=max(0,float(x.get("tax_rate",19)))
        amount=qty*price; subtotal+=amount; discount+=max(0,float(x.get("discount",0))); tax+=(amount-max(0,float(x.get("discount",0))))*rate/100
    return {"subtotal":float(q2(subtotal)),"discount":float(q2(discount)),"tax_amount":float(q2(tax)),"total_amount":float(q2(subtotal-discount+tax))}

def create_purchase_order(supplier_id, project_id, order_date, expected_date, items, notes="", status="Draft", conn=None):
    own=conn is None; c=conn or get_connection()
    try:
        if not items: raise ValueError("Purchase order must contain at least one item.")
        t=order_totals(items); po_id=next_random_id(c,"po",digits=10); num=next_random_id(c,"PO",digits=8)
        c.execute("INSERT INTO purchase_orders(purchase_order_id,order_number,supplier_id,project_id,order_date,expected_date,status,subtotal,discount,tax_amount,total_amount,notes,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", (po_id,num,supplier_id,project_id,order_date,expected_date,status,t["subtotal"],t["discount"],t["tax_amount"],t["total_amount"],notes))
        for x in items:
            iid=next_random_id(c,"poi",digits=10); qty=float(x["quantity"]); price=float(x.get("unit_price",0)); rate=float(x.get("tax_rate",19)); amount=qty*price
            c.execute("INSERT INTO purchase_order_items(purchase_order_item_id,purchase_order_id,material_id,description,quantity,unit,unit_price,tax_rate,amount,cost_center_id,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(iid,po_id,x.get("material_id"),x["description"],qty,x.get("unit"),price,rate,float(q2(amount)),x.get("cost_center_id"),x.get("notes")))
        if own:c.commit()
        return po_id
    except (sqlite3.Error, ValueError, TypeError, OSError):
        if own:c.rollback()
        raise
    finally:
        if own:c.close()

def receive_purchase_order(po_id, receipt_date, lines, warehouse="", notes="", conn=None):
    own=conn is None; c=conn or get_connection()
    try:
        r_id=next_random_id(c,"por",digits=10); number=next_random_id(c,"GRN",digits=8)
        c.execute("INSERT INTO purchase_receipts(receipt_id,purchase_order_id,receipt_number,receipt_date,warehouse,notes) VALUES(?,?,?,?,?,?)",(r_id,po_id,number,receipt_date,warehouse,notes))
        for line in lines:
            qty=float(line["quantity"]);
            if qty<=0: continue
            c.execute("INSERT INTO purchase_receipt_items(receipt_item_id,receipt_id,purchase_order_item_id,quantity,unit_cost) VALUES(?,?,?,?,?)",(next_random_id(c,"pri",digits=10),r_id,line["purchase_order_item_id"],qty,float(line.get("unit_cost",0))))
            c.execute("UPDATE purchase_order_items SET received_quantity=received_quantity+? WHERE purchase_order_item_id=?",(qty,line["purchase_order_item_id"]))
            if line.get("material_id"):
                c.execute("INSERT INTO material_movements(movement_id,material_id,project_id,movement_date,movement_type,warehouse,quantity,unit_cost,reference,notes) SELECT ?,material_id,(SELECT project_id FROM purchase_orders WHERE purchase_order_id=?),?,?,?,?,?,?,? FROM purchase_order_items WHERE purchase_order_item_id=?",(next_random_id(c,"mm",digits=10),po_id,receipt_date,"Receipt",warehouse,qty,float(line.get("unit_cost",0)),number,notes,line["purchase_order_item_id"]))
        pending=c.execute("SELECT COUNT(*) FROM purchase_order_items WHERE purchase_order_id=? AND received_quantity+0.0001 < quantity",(po_id,)).fetchone()[0]
        status="Partially Received" if pending else "Received"
        c.execute("UPDATE purchase_orders SET status=?,updated_at=CURRENT_TIMESTAMP WHERE purchase_order_id=?",(status,po_id))
        if own:c.commit()
        return r_id
    except (sqlite3.Error, ValueError, TypeError, OSError):
        if own:c.rollback()
        raise
    finally:
        if own:c.close()
