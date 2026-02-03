from django.shortcuts import render
import hmac
import hashlib
import base64
from uuid import uuid4

# Create your views here.
def paymentHandler(request):
    uid = uuid4()
    # print('UID: ',uid)
    total_amount = 110
    transaction_uuid = uid
    product_code = 'EPAYTEST'
    message = f'total_amount={total_amount},transaction_uuid={uid},product_code={product_code}'
    message = message.encode()
    secret = b"8gBm/:&EnhH.1/q"
    hmac_sha256 = hmac.new(secret, message, digestmod=hashlib.sha256)
    digest = hmac_sha256.digest()
    # print('Digest: ',digest)
    signature = base64.b64encode(digest).decode('utf-8') 
    # print('Signature: ',signature)

    context = {
        'transaction_uuid': transaction_uuid,
        'total_amount': total_amount,
        'product_code': product_code,
        'signature': signature,
    }
    return render(request, 'index.html', context=context)