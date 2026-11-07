"""Synthetic boundary challenges for the frozen Family Ledger diagnostic scope."""
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

target = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(target))
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.application.receipt_ingestion import ReceiptIngestionService
from app.domain.receipts.models import ParsedReceipt, ParsedLine, Unit
from app.infrastructure.db.orm import Base, Family, Supermarket, Product, ProductAlias, ReceiptLine
from app.infrastructure.parsers.makro import MakroParser

mode = sys.argv[2]
if mode == 'missing-date':
    raw = (target / 'tests/fixtures/makro_ticket.txt').read_text()
    parsed = MakroParser().parse(raw.replace('04/07/2026', ''))
    passed = parsed.purchase_date is None and any(x.field_path == 'purchase_date' for x in parsed.pending_fields)
    print(json.dumps({'obligation':'OBL-002','expected':'null date and pending review','purchase_date':str(parsed.purchase_date),'pending_fields':[x.field_path for x in parsed.pending_fields],'passed':passed}))
    sys.exit(0 if passed else 1)
if mode == 'family-isolation':
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        a, b = Family(name='Synthetic A'), Family(name='Synthetic B')
        shop = Supermarket(name='Synthetic Makro', parser_key='makro')
        session.add_all([a,b,shop]); session.flush()
        private_product = Product(family_id=a.id, canonical_name='Synthetic private product', default_unit='unit')
        session.add(private_product); session.flush()
        session.add(ProductAlias(product_id=private_product.id, supermarket_id=shop.id, alias_text='SYNTHETIC PRIVATE ALIAS', match_type='manual'))
        session.flush()
        parsed = ParsedReceipt(supermarket_key='makro',purchase_date=date(2026,11,7),total_amount=Decimal('1.00'),lines=[ParsedLine(line_number=1,raw_text='SYNTHETIC PRIVATE ALIAS',description='SYNTHETIC PRIVATE ALIAS',quantity=Decimal(1),unit=Unit.UNIT,unit_price=Decimal('1.00'),line_total=Decimal('1.00'))])
        result = ReceiptIngestionService(session).ingest(parsed,b.id)
        line = session.execute(select(ReceiptLine).where(ReceiptLine.receipt_id == result.receipt_id)).scalar_one()
        crossed = line.product_id == private_product.id
        print(json.dumps({'obligation':'OBL-006','expected':'family B must not resolve private product owned by A','receipt_owned_by_B':line.receipt.family_id == b.id,'resolved_private_product_owned_by_A':crossed,'passed':not crossed,'environment':'SQLite in memory; no production data; session closes without commit'}))
        sys.exit(1 if crossed else 0)
raise SystemExit('Unknown probe mode')
