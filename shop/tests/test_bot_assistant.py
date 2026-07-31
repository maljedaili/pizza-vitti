from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings
from django.urls import reverse


class BotAssistantTests(TestCase):
    def test_public_home_includes_chat_interface(self):
        response = self.client.get('/fr/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-bot-form')
        self.assertContains(response, reverse('shop:bot_reply'))

    @override_settings(OPENAI_API_KEY='')
    def test_falls_back_to_local_assistant_without_key(self):
        response = self.client.post(reverse('shop:bot_reply'), {'message': 'bonjour'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('Bonjour', response.json()['answer'])

    @override_settings(OPENAI_API_KEY='')
    def test_english_opening_question_has_relevant_fallback(self):
        response = self.client.post(reverse('shop:bot_reply'), {'message': 'are you open?'})

        self.assertEqual(response.status_code, 200)
        self.assertIn("today's opening status", response.json()['answer'])

    @override_settings(
        OPENAI_API_KEY='test-key',
        OPENAI_MODEL='gpt-5.6-sol',
        OPENAI_TIMEOUT_SECONDS=2,
    )
    @patch('shop.views.requests.post')
    def test_returns_responses_api_text(self, post):
        api_response = Mock()
        api_response.raise_for_status.return_value = None
        api_response.json.return_value = {
            'output': [{
                'type': 'message',
                'content': [{'type': 'output_text', 'text': 'Voici nos pizzas disponibles.'}],
            }],
        }
        post.return_value = api_response

        response = self.client.post(reverse('shop:bot_reply'), {'message': 'Quelles pizzas avez-vous ?'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['answer'], 'Voici nos pizzas disponibles.')
        request_payload = post.call_args.kwargs['json']
        self.assertEqual(request_payload['model'], 'gpt-5.6-sol')
        self.assertIn('Quelles pizzas', request_payload['input'])

    @override_settings(OPENAI_API_KEY='test-key', OPENAI_TIMEOUT_SECONDS=2)
    @patch('shop.views.requests.post', side_effect=requests.RequestException)
    def test_api_failure_uses_local_fallback(self, post):
        response = self.client.post(reverse('shop:bot_reply'), {'message': 'adresse'})

        self.assertEqual(response.status_code, 200)
        self.assertIn("236 Rue d'Ornano", response.json()['answer'])
