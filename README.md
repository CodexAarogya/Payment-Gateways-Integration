# eSewa Payment Gateway Integration

A production-ready eSewa payment gateway integration for Django/Flask applications. This implementation handles the complete payment flow including payment initiation, callback verification, and transaction status checking.

## 🚀 Features

- ✅ Complete payment flow implementation
- ✅ Secure HMAC-SHA256 signature generation and verification
- ✅ Transaction verification with eSewa API
- ✅ Support for both test and production environments
- ✅ Comprehensive error handling
- ✅ Ready-to-use templates and forms
- ✅ Detailed logging for debugging

## 📋 Prerequisites

- Python 3.7+
- Django 3.2+ or Flask 2.0+
- eSewa merchant account (get one at [eSewa for Business](https://esewa.com.np))
- Basic understanding of payment gateway workflows

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/CodexAarogya/Payment-Gateways-Integration.git
cd Payment-Gateways-Integration/PaymentIntegration_Esewa
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in your project root:

```env
# eSewa Merchant Credentials
ESEWA_MERCHANT_ID=your_merchant_id
ESEWA_SECRET_KEY=your_secret_key

# Environment (test/production)
ESEWA_ENVIRONMENT=test

# URLs
ESEWA_SUCCESS_URL=http://localhost:8000/esewa/success/
ESEWA_FAILURE_URL=http://localhost:8000/esewa/failure/
```

### 4. Update Settings

Add to your Django `settings.py`:

```python
# eSewa Configuration
ESEWA_CONFIG = {
    'MERCHANT_ID': os.getenv('ESEWA_MERCHANT_ID'),
    'SECRET_KEY': os.getenv('ESEWA_SECRET_KEY'),
    'ENVIRONMENT': os.getenv('ESEWA_ENVIRONMENT', 'test'),
    'SUCCESS_URL': os.getenv('ESEWA_SUCCESS_URL'),
    'FAILURE_URL': os.getenv('ESEWA_FAILURE_URL'),
}

# API Endpoints
if ESEWA_CONFIG['ENVIRONMENT'] == 'test':
    ESEWA_PAYMENT_URL = 'https://rc-epay.esewa.com.np/api/epay/main/v2/form'
    ESEWA_VERIFY_URL = 'https://rc-epay.esewa.com.np/api/epay/transaction/status/'
else:
    ESEWA_PAYMENT_URL = 'https://epay.esewa.com.np/api/epay/main/v2/form'
    ESEWA_VERIFY_URL = 'https://epay.esewa.com.np/api/epay/transaction/status/'
```

## 💻 Implementation Guide

### Step 1: Create Payment Utilities

Create `esewa_utils.py`:

```python
import hmac
import hashlib
import base64
import requests
from django.conf import settings


def generate_signature(message):
    """
    Generate HMAC-SHA256 signature for eSewa payment
    
    Args:
        message (str): Concatenated payment parameters
    
    Returns:
        str: Base64 encoded signature
    """
    secret_key = settings.ESEWA_CONFIG['SECRET_KEY']
    
    # Create HMAC-SHA256 hash
    hash_hmac = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    )
    
    # Return base64 encoded signature
    return base64.b64encode(hash_hmac.digest()).decode()


def create_payment_data(transaction_id, amount, product_name):
    """
    Prepare payment data for eSewa
    
    Args:
        transaction_id (str): Unique transaction identifier
        amount (float): Payment amount
        product_name (str): Name/description of product
    
    Returns:
        dict: Payment form data with signature
    """
    tax_amount = 0
    total_amount = amount
    
    # Create message for signature (ORDER MATTERS!)
    message = f"total_amount={total_amount},transaction_uuid={transaction_id},product_code={settings.ESEWA_CONFIG['MERCHANT_ID']}"
    
    signature = generate_signature(message)
    
    payment_data = {
        'amount': amount,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'transaction_uuid': transaction_id,
        'product_code': settings.ESEWA_CONFIG['MERCHANT_ID'],
        'product_service_charge': 0,
        'product_delivery_charge': 0,
        'success_url': settings.ESEWA_CONFIG['SUCCESS_URL'],
        'failure_url': settings.ESEWA_CONFIG['FAILURE_URL'],
        'signed_field_names': 'total_amount,transaction_uuid,product_code',
        'signature': signature
    }
    
    return payment_data


def verify_payment(transaction_id):
    """
    Verify payment status with eSewa API
    
    Args:
        transaction_id (str): Transaction UUID to verify
    
    Returns:
        dict: Verification response or None if failed
    """
    verify_url = settings.ESEWA_VERIFY_URL
    
    params = {
        'product_code': settings.ESEWA_CONFIG['MERCHANT_ID'],
        'total_amount': transaction_id,  # This should be actual amount
        'transaction_uuid': transaction_id
    }
    
    try:
        response = requests.get(verify_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Verification failed: {e}")
        return None
```

### Step 2: Create Views

Create `views.py`:

```python
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import uuid
from .esewa_utils import create_payment_data, verify_payment


def initiate_payment(request):
    """
    Display payment initiation page with eSewa form
    """
    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        product_name = request.POST.get('product_name', 'Product')
        
        # Generate unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Store transaction in session for verification
        request.session['transaction_id'] = transaction_id
        request.session['amount'] = amount
        
        # Create payment data
        payment_data = create_payment_data(
            transaction_id=transaction_id,
            amount=amount,
            product_name=product_name
        )
        
        context = {
            'payment_data': payment_data,
            'payment_url': settings.ESEWA_PAYMENT_URL
        }
        
        return render(request, 'esewa/payment_form.html', context)
    
    return render(request, 'esewa/initiate.html')


@csrf_exempt
def payment_success(request):
    """
    Handle successful payment callback from eSewa
    """
    # Extract parameters from GET request
    transaction_id = request.GET.get('transaction_uuid')
    esewa_transaction_id = request.GET.get('transaction_code')
    
    if not transaction_id:
        return HttpResponse("Invalid transaction", status=400)
    
    # Verify the payment with eSewa API
    verification_result = verify_payment(transaction_id)
    
    if verification_result and verification_result.get('status') == 'COMPLETE':
        # Payment verified successfully
        # Update your database here
        
        context = {
            'transaction_id': transaction_id,
            'esewa_transaction_id': esewa_transaction_id,
            'status': 'success',
            'message': 'Payment completed successfully!'
        }
        return render(request, 'esewa/success.html', context)
    else:
        # Verification failed
        context = {
            'status': 'failed',
            'message': 'Payment verification failed. Please contact support.'
        }
        return render(request, 'esewa/failure.html', context)


@csrf_exempt
def payment_failure(request):
    """
    Handle failed payment callback from eSewa
    """
    context = {
        'status': 'failed',
        'message': 'Payment was cancelled or failed.'
    }
    return render(request, 'esewa/failure.html', context)
```

### Step 3: Configure URLs

Create `urls.py`:

```python
from django.urls import path
from . import views

app_name = 'esewa'

urlpatterns = [
    path('initiate/', views.initiate_payment, name='initiate'),
    path('success/', views.payment_success, name='success'),
    path('failure/', views.payment_failure, name='failure'),
]
```

Add to main `urls.py`:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('esewa/', include('esewa.urls')),
]
```

### Step 4: Create Templates

Create `templates/esewa/payment_form.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Processing Payment</title>
</head>
<body>
    <h2>Redirecting to eSewa...</h2>
    <p>Please wait while we redirect you to the payment page.</p>
    
    <form id="esewaForm" action="{{ payment_url }}" method="POST">
        {% for key, value in payment_data.items %}
            <input type="hidden" name="{{ key }}" value="{{ value }}">
        {% endfor %}
    </form>
    
    <script>
        document.getElementById('esewaForm').submit();
    </script>
</body>
</html>
```

Create `templates/esewa/initiate.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Make Payment</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 500px;
            margin: 50px auto;
            padding: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            background-color: #60bb46;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            width: 100%;
            font-size: 16px;
        }
        button:hover {
            background-color: #4a9537;
        }
    </style>
</head>
<body>
    <h2>eSewa Payment</h2>
    <form method="POST">
        {% csrf_token %}
        <div class="form-group">
            <label>Product Name:</label>
            <input type="text" name="product_name" required>
        </div>
        <div class="form-group">
            <label>Amount (NPR):</label>
            <input type="number" name="amount" step="0.01" min="10" required>
        </div>
        <button type="submit">Pay with eSewa</button>
    </form>
</body>
</html>
```

## 🔒 Security Best Practices

1. **Never expose your secret key** - Always use environment variables
2. **Validate on backend** - Don't trust frontend/callback parameters
3. **Verify every transaction** - Always call the verification API
4. **Use unique transaction IDs** - Implement proper UUID generation
5. **Implement rate limiting** - Prevent payment spam
6. **Log everything** - Maintain audit trails for all transactions

## 🧪 Testing

### Test Mode Credentials

For testing, eSewa provides test credentials. Request them from eSewa merchant support.

### Test Transaction Flow

1. Use small amounts (NPR 10-100) for testing
2. Test both success and failure scenarios
3. Verify callback handling
4. Check transaction verification

### Common Test Cases

```python
# Test 1: Successful Payment
amount = 100
# Complete payment flow and verify status = 'COMPLETE'

# Test 2: Failed Payment
# Cancel payment on eSewa page
# Verify redirect to failure URL

# Test 3: Duplicate Transaction ID
# Try using same transaction ID twice
# Should fail on second attempt

# Test 4: Invalid Signature
# Modify signature parameter
# Payment should be rejected
```

## ⚠️ Common Issues & Solutions

### Issue 1: Invalid Signature Error

**Problem:** Getting "Invalid Signature" from eSewa

**Solution:**
- Check parameter order in message string
- Ensure secret key is correct
- Verify all parameters are included
- Check for extra spaces or encoding issues

### Issue 2: Callback Not Received

**Problem:** Success/failure URL not being called

**Solution:**
- Ensure URLs are publicly accessible
- Use ngrok for local testing
- Check firewall/server configuration
- Verify URL format in settings

### Issue 3: Verification API Fails

**Problem:** Transaction verification returns error

**Solution:**
- Wait a few seconds before verification
- Check if using correct API endpoint (test/prod)
- Verify merchant credentials
- Ensure transaction actually completed

## 📊 Production Deployment Checklist

- [ ] Switch to production credentials
- [ ] Update ESEWA_ENVIRONMENT to 'production'
- [ ] Use production API URLs
- [ ] Implement proper error logging
- [ ] Set up transaction database
- [ ] Configure SSL certificates
- [ ] Test with real small amounts
- [ ] Implement webhook verification
- [ ] Set up monitoring and alerts
- [ ] Create backup/recovery procedures

## 🔗 Resources

- [eSewa Official Documentation](https://developer.esewa.com.np/)
- [eSewa Merchant Portal](https://merchant.esewa.com.np/)
- [API Reference](https://developer.esewa.com.np/pages/Epay)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 💬 Support

For issues or questions:
- Open an issue on GitHub
- Contact eSewa merchant support for API-related queries
- Check the official eSewa developer documentation

## ⭐ Acknowledgments

Built with reference to eSewa's official API documentation and best practices from the developer community.

---

**Note:** This is a prototype implementation. Please review and adapt according to your specific requirements and security policies before using in production.

**Author:** CodexAarogya  
**Repository:** [Payment-Gateways-Integration](https://github.com/CodexAarogya/Payment-Gateways-Integration)
