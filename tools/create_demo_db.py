# ============================================================
# شرح الملف: tools/create_demo_db.py
# هذا الملف جزء من أدوات الفحص والتحقق المساعدة للمشروع.
# التعليقات العربية هنا للتوضيح والصيانة فقط، ولا تغيّر سلوك البرنامج.
# تم الحفاظ على أسماء الكائنات وواجهات الاستدعاء ومنطق قاعدة البيانات كما هي.
# ============================================================
# صيانة: هذا الملف جزء من BuildOffice Pro. حافظ على فصل الواجهة عن منطق البيانات، واستخدم الإعدادات المركزية عند الحاجة.
"""Create a realistic interconnected demo database for UI and workflow testing."""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.id_service import next_child_id, next_random_id, next_sequence_id
from database import database as db


# شرح الدالة build: تنفّذ خطوة منطقية مرتبطة بوظيفة هذا الملف.
def build(path: Path, arabic: bool = False) -> None:
    old=db.DATABASE_FILE; db.DATABASE_FILE=path
    try:
        for suffix in ('','-wal','-shm'):
            Path(str(path)+suffix).unlink(missing_ok=True)
        db.create_database(); c=db.get_connection(); c.execute('BEGIN IMMEDIATE')
        projects=[]
        project_specs = ([
            ('توسعة مدرسة الأبيار','DEMO-PRJ-001',12800000,'مديرية التربية بالجزائر'),
            ('إعادة تأهيل الطريق البلدي بالبليدة','DEMO-PRJ-002',7600000,'بلدية البليدة'),
            ('أشغال شبكة المياه بتيبازة','DEMO-PRJ-003',5400000,'الجزائرية للمياه - تيبازة'),
        ] if arabic else [
            ('School Extension - El Biar','DEMO-PRJ-001',12800000,'Algiers Education Directorate'),
            ('Municipal Road Rehabilitation - Blida','DEMO-PRJ-002',7600000,'Blida Municipality'),
            ('Water Network Works - Tipaza','DEMO-PRJ-003',5400000,'ADE Tipaza'),
        ])
        project_types = ['توسعة', 'تجديد طرقات', 'شبكات المياه'] if arabic else ['Public Works'] * 3
        project_locations = ['الجزائر العاصمة', 'البليدة', 'تيبازة'] if arabic else ['Algeria'] * 3
        for name,code,budget,authority in project_specs:
            pid=next_sequence_id(c,'prj',digits=3); projects.append(pid)
            c.execute("INSERT INTO projects(project_id,project_name,summarised_name,contracting_authority,project_type,contract_code,contract_date,start_date,period,end_date,budget_ht,tva_percent,tva,budget_ttc,status,location,description) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (pid,name,name[:28],authority,project_types[len(projects)-1],code,'2026-06-01','2026-07-01',240,'2027-02-26',budget,19,budget*.19,budget*1.19,'Active',project_locations[len(projects)-1],f'مشروع أشغال عمومية تجريبي: {name}.' if arabic else f'Demo construction project for {name}.'))

        staff=[]
        staff_specs = ([
            ('أحمد بن علي','مهندس موقع','On Site',5200),('كريم السعيدي','رئيس ورشة','On Site',4300),('ياسين مزيان','بنّاء','On Site',3800),('سمير بلقاسم','سائق','On Site',3600),('نادية العمراني','محاسبة','Administration',6000),('إيمان حداد','مسؤولة وثائق','Administration',4800),('عمر قاسي','مسّاح','On Site',5000)
        ] if arabic else [
            ('Ahmed Benali','Site Engineer','On Site',5200),('Karim Saidi','Foreman','On Site',4300),('Yacine Meziane','Mason','On Site',3800),('Samir Belkacem','Driver','On Site',3600),('Nadia Amrani','Accountant','Administration',6000),('Imane Haddad','Document Controller','Administration',4800),('Omar Kaci','Surveyor','On Site',5000)
        ])
        for name,role,atype,rate in staff_specs:
            sid=next_sequence_id(c,'stf',digits=3); staff.append(sid)
            c.execute("INSERT INTO staff(staff_id,full_name,position,employment_type,salary_type,rate,hire_date,status,attendance_type) VALUES(?,?,?,?,?,?,?,?,?)",
                      (sid,name,role,'Full Time','Monthly',rate,'2025-01-15','Active',atype))
            for pid in projects[:2] if sid in staff[:5] else projects[1:]:
                c.execute("INSERT INTO staff_projects(staff_id,project_id,active,assignment_start_date,role_on_project) VALUES(?,?,?,?,?)",(sid,pid,1,'2026-07-01',role))

        items=[]
        item_specs=[
            ('01','Site installation','unit',1,250000),('02','Excavation','m3',1800,950),('03','Backfilling','m3',1100,620),('04','Reinforced concrete','m3',620,21000),('05','Formwork','m2',4100,1850),
            ('06','Rebar supply and fixing','t',88,165000),('07','Masonry walls','m2',3600,2250),('08','Plastering','m2',5200,900),('09','Painting','m2',6400,720),('10','Ceramic floor','m2',1850,3100),
            ('11','Road excavation','m3',2500,780),('12','Aggregate base','m3',2100,1650),('13','Asphalt layer','t',980,11800),('14','Curbs','ml',3200,1250),('15','Water pipe DN200','ml',2400,5200),('16','Valve chamber','unit',18,28500),
            ('17','Testing and commissioning','lot',1,145000),('18','Site cleaning','lot',1,58000)]
        if arabic:
            item_specs = [
                ('01','تنصيب الورشة','unit',1,250000),('02','حفر','m3',1800,950),('03','ردم','m3',1100,620),('04','خرسانة مسلحة','m3',620,21000),('05','قوالب','m2',4100,1850),
                ('06','توريد وتركيب حديد التسليح','t',88,165000),('07','جدران مبنية','m2',3600,2250),('08','طلاء أسمنتي','m2',5200,900),('09','دهان','m2',6400,720),('10','أرضية خزفية','m2',1850,3100),
                ('11','حفر الطريق','m3',2500,780),('12','طبقة أساس حصوية','m3',2100,1650),('13','طبقة إسفلتية','t',980,11800),('14','أرصفة','ml',3200,1250),('15','أنبوب مياه DN200','ml',2400,5200),('16','غرفة صمام','unit',18,28500),
                ('17','اختبار ووضع المنشأة في الخدمة','lot',1,145000),('18','تنظيف الورشة','lot',1,58000)]
        for pid in projects:
            for num,desc,unit,qty,price in item_specs[:6] if pid==projects[0] else item_specs[6:12] if pid==projects[1] else item_specs[12:]:
                iid=next_child_id(c,'mtr',pid,digits=3); items.append((iid,pid))
                c.execute("INSERT INTO metre_items(item_id,project_id,item_number,description,unit,quantity,unit_price,amount) VALUES(?,?,?,?,?,?,?,?)",(iid,pid,num,desc,unit,qty,price,qty*price))
            # supplement each project to 6 exactly
        
        expense_categories=['Materials','Transport','Fuel','Equipment','Labor','Services','Office','Maintenance']
        expense_labels=['مواد','نقل','وقود','معدات','أجور','خدمات','مكتب','صيانة'] if arabic else expense_categories
        expenses=[]
        for i in range(18):
            pid=projects[i%3] if i%4!=0 else None
            eid=next_child_id(c,'exp',pid if pid else 'gen',digits=3)
            total=[185000,240000,72000,315000,98000,145000][i%6]
            desc=f"مصروف تجريبي {i+1:02d} - {expense_labels[i%len(expense_labels)]}" if arabic else f"Demo expense {i+1:02d} - {expense_categories[i%len(expense_categories)]}"
            due=(date(2026,9,2)+timedelta(days=i)).isoformat()
            c.execute("INSERT INTO expenses(expense_id,project_id,date,description,category,amount,due_date,payment_status,payment_method,notes) VALUES(?,?,?,?,?,?,?,?,?,?)",(eid,pid,(date(2026,8,20)+timedelta(days=i)).isoformat(),desc,expense_categories[i%len(expense_categories)],total,due,('Credit' if i % 3 == 0 else 'Partial Payment' if i % 3 == 1 else 'Paid'),'Bank Transfer','سجل تجريبي' if arabic else 'Demo record'))
            expenses.append((eid,total))
            if i%3==0 or i%3==1:
                paid=total if i%4==0 else round(total*.45,2)
                pay=next_child_id(c,'pay',eid,digits=6)
                c.execute("INSERT INTO expense_payments(payment_id,expense_id,payment_date,amount,payment_method,reference) VALUES(?,?,?,?,?,?)",(pay,eid,(date(2026,8,25)+timedelta(days=i)).isoformat(),paid,'Bank Transfer',f'EXP-PAY-{i+1:03d}'))

        for i in range(10):
            pid=projects[i%3]; iid=next_sequence_id(c,'incm',digits=3)
            c.execute("INSERT INTO project_payments(payment_id,project_id,date,amount,payment_method,reference,notes) VALUES(?,?,?,?,?,?,?)",(iid,pid,(date(2026,7,25)+timedelta(days=i*7)).isoformat(),750000+i*85000,'Bank Transfer',f'SIT-REC-{i+1:03d}','دفعة مرحلية تجريبية' if arabic else 'Progress payment demo'))

        for i in range(5):
            did=next_sequence_id(c,'dbt',digits=3); total=90000+i*27500; pid=projects[i%3]
            c.execute("INSERT INTO debt(debt_id,project_id,lender,date,due_date,amount,status,notes) VALUES(?,?,?,?,?,?,?,?)",(did,pid,('مورد تجريبي ' if arabic else 'Demo Supplier ')+str(i+1),(date(2026,8,1)+timedelta(days=i)).isoformat(),(date(2026,9,10)+timedelta(days=i*5)).isoformat(),total,'Open','ائتمان مورد تجريبي' if arabic else 'Demo supplier credit'))
            if i<4:
                dp=next_child_id(c,'pay',did,digits=6); c.execute("INSERT INTO debt_payments(payment_id,debt_id,payment_date,amount,payment_method,reference) VALUES(?,?,?,?,?,?)",(dp,did,'2026-08-28',round(total*.3,2),'Cash',f'DBT-PAY-{i+1:03d}'))

        for i in range(20):
            sid=staff[i%len(staff)]; pid=projects[i%3] if i%5 else None; aid=next_child_id(c,'att',sid,pid or 'adm',digits=6)
            c.execute("INSERT INTO attendance(record_id,staff_id,project_id,date,working_hours,overtime_hours,status,notes) VALUES(?,?,?,?,?,?,?,?)",(aid,sid,pid,(date(2026,9,1)+timedelta(days=i%7)).isoformat(),8,1.5 if i%6==0 else 0,'Present' if i%9 else 'Leave','حضور تجريبي'))

        for sid in staff[:5]:
            for period,base in [('2026-08',52000),('2026-09',54000)]:
                py=next_random_id(c,'prl',digits=10); ot=6500 if sid in staff[:3] else 0; bonus=2500
                net=base+ot+bonus-1200
                c.execute("INSERT INTO payroll_records(payroll_id,staff_id,period,base_amount,overtime_amount,bonuses,deductions,advances,net_amount,status) VALUES(?,?,?,?,?,?,?,?,?,?)",(py,sid,period,base,ot,bonus,1200,0,net,'Draft'))

        vehicles=[]
        for i,(brand,model,plate) in enumerate([('Toyota','Hilux','00111-116-16'),('Isuzu','D-Max','00222-116-16'),('Renault','Master','00333-116-16'),('MAN','TGM','00444-116-16')]):
            vid=next_sequence_id(c,'vhc',digits=3); vehicles.append(vid)
            c.execute("INSERT INTO vehicles(vehicle_id,brand,model,vin,serial_number,licence_plate,buy_date,current_project_id,status,notes) VALUES(?,?,?,?,?,?,?,?,?,?)",(vid,brand,model,f'WVWDEMO{i+1:06d}',f'SN-DEMO-{i+1:04d}',plate,'2024-03-15',projects[i%3],'Active','مركبة أسطول تجريبية' if arabic else 'Demo fleet vehicle'))
            for j in range(2):
                mid=next_child_id(c,'mtn',vid,digits=6); c.execute("INSERT INTO maintenance_records(maintenance_id,vehicle_id,maintenance_date,maintenance_type,description,cost,mileage,next_maintenance_date,project_id) VALUES(?,?,?,?,?,?,?,?,?)",(mid,vid,(date(2026,7,20)+timedelta(days=j*35)).isoformat(),'Preventive','صيانة دورية' if arabic else 'Routine maintenance',18000+j*4500,65000+j*3500,(date(2026,10,1)+timedelta(days=j*30)).isoformat(),projects[i%3]))
                fid=next_child_id(c,'fuel',vid,digits=6); qty=75+j*10; price=45
                c.execute("INSERT INTO fuel_records(fuel_id,vehicle_id,date,quantity,unit_price,total_cost,mileage,project_id) VALUES(?,?,?,?,?,?,?,?)",(fid,vid,(date(2026,8,5)+timedelta(days=j*25)).isoformat(),qty,price,qty*price,67000+j*3500,projects[i%3]))

        # 3 situations, each populated with 3 items and safe quantities.
        for si,pid in enumerate(projects,1):
            qitems=c.execute("SELECT item_id,quantity,unit_price FROM metre_items WHERE project_id=? ORDER BY item_number LIMIT 3",(pid,)).fetchall()
            sit=next_child_id(c,'sit',pid,digits=3)
            c.execute("INSERT INTO situations(situation_id,project_id,situation_number,situation_date,title,status) VALUES(?,?,?,?,?,?)",(sit,pid,si,f'2026-09-0{si}',f'الوضعية {si}' if arabic else f'Situation {si}','Draft'))
            for row in qitems:
                qty=min(float(row['quantity'])*.2, float(row['quantity'])); sii=next_child_id(c,'sitm',sit,digits=6)
                c.execute("INSERT INTO situation_items(situation_item_id,situation_id,item_id,executed_quantity,unit_price,amount,previous_quantity) VALUES(?,?,?,?,?,?,?)",(sii,sit,row['item_id'],qty,row['unit_price'],qty*row['unit_price'],0))

        # Unified documents metadata, using real temp paths only as demo metadata.
        docs=[('company',None,'نسخة من السجل التجاري','Legal','2026-01-10','2027-01-10'),('project',projects[0],'عقد توسعة المدرسة','Contract','2026-06-01','2027-02-26'),('project',projects[1],'تأمين الورشة','Insurance','2026-06-15','2026-12-15'),('staff',staff[0],'عقد عمل','HR','2025-01-15','2027-01-15'),('vehicle',vehicles[0],'تأمين المركبة','Insurance','2026-03-01','2027-03-01'),('general',None,'عقد إيجار المكتب','Lease','2026-01-01','2026-12-31')] if arabic else [('company',None,'Company registration copy','Legal','2026-01-10','2027-01-10'),('project',projects[0],'Contract - School Extension','Contract','2026-06-01','2027-02-26'),('project',projects[1],'Site insurance','Insurance','2026-06-15','2026-12-15'),('staff',staff[0],'Employment contract','HR','2025-01-15','2027-01-15'),('vehicle',vehicles[0],'Vehicle insurance','Insurance','2026-03-01','2027-03-01'),('general',None,'Office lease','Lease','2026-01-01','2026-12-31')]
        for owner,oid,name,cat,issue,expiry in docs:
            did=next_sequence_id(c,'doc',digits=3); c.execute("INSERT INTO documents(document_id,owner_type,owner_id,document_name,file_path,category,issue_date,expiry_date,reminder_days,status,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(did,owner,oid,name,str(ROOT/'resources'/'logo.png'),cat,issue,expiry,30,'Active','Demo metadata; file path points to packaged resource.'))

        c.commit(); c.close()
    finally: db.DATABASE_FILE=old

if __name__=='__main__':
    arabic = '--arabic' in sys.argv[1:]
    arguments = [arg for arg in sys.argv[1:] if arg != '--arabic']
    target=Path(arguments[0]).resolve() if arguments else ROOT/('buildoffice_demo_ar.db' if arabic else 'buildoffice_demo.db')
    build(target, arabic=arabic); print(target)
