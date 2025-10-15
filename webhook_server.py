# --- webhook_server.py (PRODUCTION VERSION - Never Sleeps) ---

from flask import Flask, request, jsonify
import os
from supabase import create_client

app = Flask(__name__)

# Get environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Initialize Supabase (do this once at startup, not per request)
supabase = None
try:
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Supabase client initialized successfully")
    else:
        print("❌ ERROR: Supabase credentials missing")
except Exception as e:
    print(f"❌ CRITICAL ERROR initializing Supabase: {e}")

@app.route('/')
def home():
    """Health check endpoint - Typeform will ping this to verify webhook is alive."""
    return jsonify({
        'status': 'online',
        'service': 'CallFlex AI Webhook Server',
        'version': '1.0',
        'supabase_connected': supabase is not None
    }), 200

@app.route('/health')
def health():
    """Alternative health check (some services prefer /health)."""
    return jsonify({'status': 'healthy'}), 200

@app.route('/typeform-webhook', methods=['POST'])
def handle_typeform_submission():
    """
    Receives Typeform submissions and saves client data to Supabase.
    
    Expected payload from Typeform:
    {
        "form_response": {
            "answers": [
                {"text": "Business Name"},
                {"email": "client@example.com"},
                {"text": "Dentists"},
                {"text": "Austin TX"}
            ]
        }
    }
    """
    try:
        # Log that we received a webhook (helps with debugging)
        print("📥 Received Typeform webhook")
        
        # Check if Supabase is connected
        if not supabase:
            print("❌ ERROR: Supabase not initialized")
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Get the JSON data from Typeform
        data = request.json
        
        if not data:
            print("❌ ERROR: No JSON data received")
            return jsonify({'error': 'No data received'}), 400
        
        # Extract answers from Typeform payload
        answers = data.get('form_response', {}).get('answers', [])
        
        if len(answers) < 4:
            print(f"❌ ERROR: Not enough answers (got {len(answers)}, need 4)")
            return jsonify({'error': 'Incomplete form submission'}), 400
        
        # Map answers to database fields
        # IMPORTANT: These indices match your Typeform question order
        business_name = answers[0].get('text', 'Unknown Business')
        contact_email = answers[1].get('email', 'no-email@example.com')
        prospecting_niche = answers[2].get('text', 'Not specified')
        prospecting_location = answers[3].get('text', 'Not specified')
        
        print(f"📝 Processing client: {business_name}")
        
        # Prepare data for Supabase
        client_data = {
            'business_name': business_name,
            'contact_email': contact_email,
            'prospecting_niche': prospecting_niche,
            'prospecting_location': prospecting_location,
            'subscription_status': 'trialing',  # They start on a trial
            'monthly_plan': 'pro'
        }
        
        # Save to Supabase
        response = supabase.table('clients').insert(client_data).execute()
        
        print(f"✅ SUCCESS: Client '{business_name}' saved to database")
        
        return jsonify({
            'status': 'success',
            'message': f'Client {business_name} added successfully',
            'client_id': response.data[0]['id'] if response.data else None
        }), 200
    
    except Exception as e:
        print(f"❌ ERROR processing Typeform webhook: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/stripe-webhook', methods=['POST'])
def handle_stripe_payment():
    """
    Receives Stripe payment confirmations.
    When a client pays, update their subscription_status to 'active'.
    
    TODO: Add Stripe webhook signature verification for security.
    """
    try:
        print("💳 Received Stripe webhook")
        
        if not supabase:
            return jsonify({'error': 'Database connection failed'}), 500
        
        data = request.json
        event_type = data.get('type')
        
        print(f"📋 Stripe event type: {event_type}")
        
        # Handle successful checkout
        if event_type == 'checkout.session.completed':
            customer_email = data.get('data', {}).get('object', {}).get('customer_details', {}).get('email')
            
            if customer_email:
                print(f"🔄 Activating client: {customer_email}")
                
                # Update client status to 'active'
                supabase.table('clients').update({
                    'subscription_status': 'active'
                }).eq('contact_email', customer_email).execute()
                
                print(f"✅ Client {customer_email} activated successfully")
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        print(f"❌ ERROR processing Stripe webhook: {e}")
        return jsonify({'error': str(e)}), 500

# This is required for Gunicorn (production server)
if __name__ == '__main__':
    # Get port from environment (Koyeb sets this automatically)
    port = int(os.getenv('PORT', 5000))
    
    print(f"🚀 Starting CallFlex AI Webhook Server on port {port}")
    print(f"🔗 Webhook endpoints:")
    print(f"   - Typeform: https://your-domain.koyeb.app/typeform-webhook")
    print(f"   - Stripe: https://your-domain.koyeb.app/stripe-webhook")
    print(f"   - Health check: https://your-domain.koyeb.app/health")
    
    # Run Flask app
    # debug=False for production, True for local testing
    app.run(host='0.0.0.0', port=port, debug=False)
