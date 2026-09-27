import unittest
import sqlite3
import json
from app import app, init_db, get_db
from ai_assistant import generate_ai_response, get_ngo_context

class TestAIAssistant(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            init_db()

    def tearDown(self):
        self.app.config['TESTING'] = False

    def test_ngo_context_retrieval(self):
        context = get_ngo_context()
        self.assertIn("Active Campaigns:", context)
        self.assertIn("Shelter Children", context)

    def test_ai_response_generation(self):
        web_resp = generate_ai_response("How can I make a donation?", channel='web')
        self.assertTrue(len(web_resp) > 10)
        self.assertIn("Ray of Trust", web_resp)

        wa_resp = generate_ai_response("Tell me about active campaigns", channel='whatsapp')
        self.assertTrue(len(wa_resp) > 10)

        voice_resp = generate_ai_response("I want to know about tax receipts", channel='voice')
        self.assertTrue(len(voice_resp) > 10)
        # Voice response should not contain markdown asterisks
        self.assertNotIn("**", voice_resp)

    def test_multilingual_responses(self):
        languages = ['English', 'Hindi', 'Marathi', 'Gujarati', 'Tamil', 'Telugu', 'Bengali', 'Spanish', 'French', 'German']
        for lang in languages:
            resp = generate_ai_response("How can I donate?", channel='web', language=lang)
            self.assertTrue(len(resp) > 10, f"Response empty for language {lang}")

    def test_web_chat_endpoint(self):
        res = self.client.post('/api/ai_chat', data=json.dumps({
            'message': 'How do I celebrate a birthday with shelter kids?',
            'language': 'Hindi'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('response', data)

    def test_whatsapp_webhook_endpoint(self):
        res = self.client.post('/api/whatsapp/webhook', data={
            'From': 'whatsapp:+919876543210',
            'Body': 'What are your active campaigns?'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('xml', res.headers['Content-Type'].lower())
        self.assertIn('<Response>', res.get_data(as_text=True))
        self.assertIn('<Message>', res.get_data(as_text=True))

    def test_voice_webhook_endpoint(self):
        res = self.client.post('/api/voice/webhook', data={'From': '+919876543210'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('xml', res.headers['Content-Type'].lower())
        self.assertIn('<Gather', res.get_data(as_text=True))

    def test_voice_gather_endpoint(self):
        res = self.client.post('/api/voice/gather', data={
            'From': '+919876543210',
            'SpeechResult': 'Tell me about 80G tax exemption'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('<Say voice="Polly.Aditi">', res.get_data(as_text=True))

if __name__ == '__main__':
    unittest.main()
