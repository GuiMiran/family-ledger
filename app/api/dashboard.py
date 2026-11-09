# @spectra US-009
"""Read model for the family app; recorded purchases are not complete spending."""
import uuid
from datetime import date
from decimal import Decimal
from fastapi import Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.auth import current_family
from app.infrastructure.db.orm import Family,Receipt,Supermarket


def install_dashboard_routes(api,database):
    @api.get('/api/v1/dashboard')
    def dashboard(family_id:uuid.UUID=Depends(current_family),session:Session=Depends(database)):
        if session.get(Family,family_id) is None:
            raise HTTPException(403,'Family is not provisioned')
        today=date.today()
        end=today.year*12+today.month-1
        months={f'{number//12:04d}-{number%12+1:02d}':{'total':Decimal(0),'count':0} for number in range(end-5,end+1)}
        rows=session.execute(select(Receipt,Supermarket.name).outerjoin(Supermarket,Receipt.supermarket_id==Supermarket.id)
                             .where(Receipt.family_id==family_id)).all()
        confirmed=[(r,name) for r,name in rows if r.status=='confirmed' and r.purchase_date is not None]
        stores={}
        total=Decimal(0)
        for receipt,name in confirmed:
            amount=receipt.total_amount or Decimal(0)
            total+=amount
            period=receipt.purchase_date.strftime('%Y-%m')
            if period in months:
                months[period]['total']+=amount;months[period]['count']+=1
            # A generic label does not invent the supermarket for unmatched input.
            key=name or 'Supermercado sin identificar'
            group=stores.setdefault(key,{'total':Decimal(0),'count':0})
            group['total']+=amount;group['count']+=1
        return {'confirmed_total':format(total,'.2f'),'confirmed_count':len(confirmed),
                'pending_count':sum(r.status=='pending_review' for r,_ in rows),
                'monthly':[{'period':period,'total':format(value['total'],'.2f'),'count':value['count']} for period,value in months.items()],
                'by_supermarket':[{'name':name,'total':format(value['total'],'.2f'),'count':value['count']} for name,value in sorted(stores.items())],
                'coverage':'confirmed_stored_receipts_only','savings':None,'waste':None,'confirmed_discounts':None}
