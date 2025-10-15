# --- webhook_server.py (FREE ZAPIER REPLACEMENT) ---
# This receives Typeform submissions and saves them to Supabase.
# Deploy this on Railway.app (free tier) or Render.com (free tier)

from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

app = Flask(__name__)

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

@app.route('/')
def home():
    """Health check endpoint."""
    return "CallFlex AI Webhook Server is running! 🚀"

@app.route('/typeform-webhook', methods=['POST'])
def handle_typeform_submission():
    """
    Receives Typeform submissions and saves client data to Supabase.
    
    Typeform sends data in this format:
    {
        "form_response": {
            "answers": [
                {"text": "Business Name Here"},
                {"email": "client@example.com"},
                {"text": "Plumbers"},
                {"text": "Austin TX"}
            ]
        }
    }
    """
    try:
        data = request.json
        
        # Extract answers from Typeform payload
        answers = data.get('form_response', {}).get('answers', [])
        
        if len(answers) < 4:
            return jsonify({'error': 'Not enough answers in form'}), 400
        
        # Map answers to database fields (adjust indices based on your form)
        business_name = answers[0].get('text', 'Unknown Business')
        contact_email = answers[1].get('email', 'no-email@example.com')
        prospecting_niche = answers[2].get('text', 'Not specified')
        prospecting_location = answers[3].get('text', 'Not specified')
        
        # Save to Supabase
        client_data = {
            'business_name': business_name,
            'contact_email': contact_email,
            'prospecting_niche': prospecting_niche,
            'prospecting_location': prospecting_location,
            'subscription_status': 'trialing',  # They start on a trial
            'monthly_plan': 'pro'
        }
        
        response = supabase.table('clients').insert(client_data).execute()
        
        print(f"✅ New client saved: {business_name}")
        
        return jsonify({
            'status': 'success',
            'message': f'Client {business_name} added successfully'
        }), 200
    
    except Exception as e:
        print(f"❌ ERROR processing webhook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/stripe-webhook', methods=['POST'])
def handle_stripe_payment():
    """
    Receives Stripe payment confirmations.
    When a client pays, update their subscription_status to 'active'.
    
    TODO: Implement Stripe webhook signature verification for security.
    """
    try:
        data = request.json
        
        # Stripe sends event type in 'type' field
        event_type = data.get('type')
        
        if event_type == 'checkout.session.completed':
            # Extract customer email from Stripe payload
            customer_email = data.get('data', {}).get('object', {}).get('customer_details', {}).get('email')
            
            if customer_email:
                # Update client status to 'active'
                supabase.table('clients').update({
                    'subscription_status': 'active'
                }).eq('contact_email', customer_email).execute()
                
                print(f"✅ Client {customer_email} payment confirmed. Status: active")
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        print(f"❌ ERROR processing Stripe webhook: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # For local testing
    app.run(host='0.0.0.0', port=5000, debug=True)
