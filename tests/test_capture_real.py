"""Real local OCR against a newly rendered synthetic receipt, never a household photo."""
from io import BytesIO
from pathlib import Path
import shutil,subprocess
import pytest
from PIL import Image,ImageDraw,ImageFont
from fastapi.testclient import TestClient
from sqlalchemy import func,select
from app.core.auth import issue_family_token
from app.infrastructure.db.orm import Family,Receipt,InventoryEntry
from app.main import create_app


def test_real_photo_to_review_purchase_and_inventory():
    if not shutil.which('tesseract'):
        pytest.skip('Local Tesseract binary required; CI installs it')
    languages=subprocess.run(['tesseract','--list-langs'],capture_output=True,text=True,check=True).stdout.splitlines()
    if not {'spa','cat','eng'}<=set(languages):
        pytest.skip('Local Spanish/Catalan/English OCR data required; CI installs it')
    font_path=Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
    if not font_path.is_file():
        pytest.skip('Synthetic receipt rendering font required; CI installs it')
    lines=(Path(__file__).parent/'fixtures/mercadona_ticket.txt').read_text().splitlines()
    image=Image.new('RGB',(2100,len(lines)*48+80),'white')
    draw=ImageDraw.Draw(image);font=ImageFont.truetype(str(font_path),32)
    for index,line in enumerate(lines):draw.text((30,30+index*48),line,font=font,fill='black')
    file=BytesIO();image.save(file,format='PNG')
    secret='synthetic-real-ocr-test-secret-over-32-characters'
    app=create_app('sqlite://',secret,initialize_schema=True)
    with app.state.sessions.begin() as session:
        family=Family(name='Synthetic OCR');session.add(family);session.flush();fid=family.id
    headers={'Authorization':'Bearer '+issue_family_token(secret,fid)}
    with TestClient(app) as client:
        result=client.post('/api/v1/receipts/extract',headers=headers,files={'image':('synthetic.png',file.getvalue(),'image/png')})
        assert result.status_code==200,result.text
        data=result.json();assert data['ocr']=={'provider':'tesseract','confidence':None}
        draft=data['parsed_receipt'];assert len(draft['lines'])==6 and draft['total_amount']=='32.24'
        with app.state.sessions() as session:
            assert session.scalar(select(func.count()).select_from(Receipt))==0
        saved=client.post('/api/v1/receipts',headers={**headers,'Idempotency-Key':'synthetic-ocr-purchase'},json=draft)
        assert saved.status_code==201,saved.text
        assert saved.json()['status']=='confirmed'
        assert len(client.get('/api/v1/inventory',headers=headers).json()['items'])==6
        assert client.get('/api/v1/dashboard',headers=headers).json()['confirmed_total']=='32.24'
        repeated=client.post('/api/v1/receipts',headers={**headers,'Idempotency-Key':'synthetic-ocr-purchase'},json=draft)
        assert repeated.status_code==201 and repeated.json()['id']==saved.json()['id']
        with app.state.sessions() as session:
            assert session.scalar(select(func.count()).select_from(InventoryEntry))==6
    app.state.engine.dispose()
