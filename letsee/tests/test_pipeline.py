import unittest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app
from backend.pipeline.analysis import analyze
from backend.pipeline.parsing import parse_messages, is_group_event, _extract_links
from backend.pipeline.validation import validate_analysis_evidence, EvidenceValidationError

class UnmissedTests(unittest.TestCase):
    def test_multiline_and_sender_timestamp_parsing(self):
        ms=parse_messages("10/09/26, 9:30 AM - Maya: Please send the report today\nwith the final chart")
        self.assertEqual(len(ms),1); self.assertEqual(ms[0]['sender'],'Maya'); self.assertEqual(ms[0]['timestamp'],'10/09/26, 9:30 AM'); self.assertIn('final chart',ms[0]['text'])
    def test_classification_and_exact_evidence(self):
        r=analyze("10/09/26, 9:00 AM - Maya: Please send your email ID today.")
        f=r['categories']['IMPORTANT'][0]; self.assertEqual(f['sources'][0]['text'],'Please send your email ID today.'); self.assertEqual(f['sources'][0]['sender'],'Maya')
    def test_group_events_excluded_but_human_responsibility_kept(self):
        r=analyze("[10/09/26, 9:00:12 AM] - Alex joined via invite link\n[10/09/26, 9:01:13 AM] - Sam: Since Alex joined the group, please ask them to own the design review.")
        all_sources=[s for group in r['categories'].values() for f in group for s in f['sources']]
        self.assertEqual(len(all_sources),1); self.assertIn('own the design review',all_sources[0]['text'])
    def test_deadline_conflict_disclosed(self):
        r=analyze("10/09/26, 9:00 AM - Maya: Submission deadline is 10/12.\n10/09/26, 9:01 AM - Raj: Submission deadline is 10/14.")
        self.assertTrue(any('conflict' in x.lower() for x in r['overview']))
        self.assertTrue(all('unresolved' in f['explanation'] for f in r['categories']['IMPORTANT']))
    def test_distinct_deadline_subjects_are_not_connected(self):
        r=analyze("10/09/26, 9:00 AM - Maya: Report deadline is 10/12.\n10/09/26, 9:01 AM - Raj: Applications deadline is 10/14.")
        self.assertFalse(any('conflict' in x.lower() for x in r['overview']))
    def test_module_numbers_keep_their_own_deadlines(self):
        result=analyze("10/09/26, 9:00 AM - Jo: Complete Module 2 by 10/12.\n10/09/26, 9:01 AM - Mo: Complete Module 3 by 10/14.")
        self.assertFalse(any('conflict' in line.lower() for line in result['overview']))
    def test_pure_system_event_is_empty_honest_state(self):
        r=analyze("10/09/26, 9:00 AM - Alex joined via invite link\n10/09/26, 9:01 AM - Mira left")
        self.assertTrue(all(not x for x in r['categories'].values())); self.assertIn('Only group-membership',r['overview'][1])
    def test_membership_events_never_become_topic_items(self):
        result=analyze("[10/09/26, 9:00 AM] - Alex joined via invite link\n[10/09/26, 9:01 AM] - Sam added Pat\n[10/09/26, 9:02 AM] - Lee left")
        self.assertEqual(sum(map(len,result['categories'].values())),0)
    def test_recruitment_kept_as_fyi_and_not_auto_promoted(self):
        r=analyze("10/01/26, 9:00 AM - Lee: Older recruitment: volunteer applications open.\n10/09/26, 9:00 AM - Pat: New ad: hiring interns this summer.")
        self.assertEqual(len(r['categories']['FYI']),2)
    def test_forwarded_message_and_decision_stay_evidence_linked(self):
        text="10/09/26, 9:00 AM - Mo: Forwarded: Office closed Friday.\n10/09/26, 9:01 AM - Mo: We decided to move the review to Tuesday."
        r=analyze(text)
        self.assertEqual(len(r['categories']['FYI']),1)
        self.assertEqual(r['categories']['FYI'][0]['sources'][0]['text'],'Forwarded: Office closed Friday.')
        self.assertEqual(len(r['categories']['IMPORTANT']),1)
        self.assertEqual(r['categories']['IMPORTANT'][0]['sources'][0]['text'],'We decided to move the review to Tuesday.')
    def test_casual_only_conversation_has_empty_categories(self):
        r=analyze("10/09/26, 9:00 AM - Mo: haha\n10/09/26, 9:01 AM - Jo: see you")
        self.assertEqual(r['categories'],{'URGENT':[],'IMPORTANT':[],'FYI':[]})
    def test_invalid_and_empty_inputs(self):
        for text in ('','not a WhatsApp header'):
            with self.assertRaises(ValueError): analyze(text)
    def test_no_unprovided_sources_or_replacement_claims(self):
        text="10/09/26, 9:00 AM - Nia: Poll: should we meet Friday?"
        r=analyze(text); f=r['categories']['IMPORTANT'][0]
        self.assertEqual(f['sources'][0]['text'],parse_messages(text)[0]['text']); self.assertEqual(f['title'],text.split(': ',1)[1])
    def test_whatsapp_export_with_seconds_and_bracketed_timestamp(self):
        messages=parse_messages("[10/5/26, 4:08:33 PM] - Maya: Hi\n[10/5/26, 4:09:02 PM] Maya: continued")
        self.assertEqual(len(messages),2)
        self.assertEqual(messages[0]['timestamp'],'10/5/26, 4:08:33 PM')
        self.assertEqual(messages[1]['sender'],'Maya')
        self.assertEqual(messages[1]['text'],'continued')
    def test_whatsapp_sender_without_dash_and_adjacent_system_events(self):
        conversation=("[10/5/26, 4:08:33 PM] +91 12345 67890: Hello\n"
                      "[10/5/26, 4:09:02 PM] - Maya joined via invite link\n"
                      "[10/5/26, 4:10:02 PM] Maya: Please send the report today.")
        messages=parse_messages(conversation)
        self.assertEqual(len(messages),3)
        self.assertEqual(messages[0]['sender'],'+91 12345 67890')
        self.assertTrue(is_group_event(messages[1]))
        self.assertEqual(messages[2]['text'],'Please send the report today.')
    def test_uploaded_txt_content_is_readable_and_analyzable(self):
        content="[10/5/26, 4:08:33 PM] - Maya: Please send the email ID today."
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'chat.txt'
            path.write_text(content,encoding='utf-8')
            result=analyze(path.read_text(encoding='utf-8'))
        finding=result['categories']['IMPORTANT'][0]
        self.assertEqual(finding['sources'][0]['text'],'Please send the email ID today.')
        self.assertEqual(finding['sources'][0]['timestamp'],'10/5/26, 4:08:33 PM')
    def test_feedback_task_gets_specific_heading_reason_link_and_exact_source(self):
        message=("[10/7/26, 5:14:39 PM] Maya: Hey everyone! Huge thanks for participating.\n"
                 "To help us make Day 2 even better, please take a minute to fill out the Day 1 Feedback Form:\n"
                 "https://docs.google.com/forms/d/e/1FAIpQLSeSnC83-GUGYmsA9Ntybn9QRqJAPW4y4OFbEtI25VIYK9eg3g/viewform?usp=dialog\n"
                 "We will use your input to improve tomorrow's session.")
        result=analyze(message)
        finding=result['categories']['IMPORTANT'][0]
        self.assertEqual(finding['title'],'Complete the Day 1 Feedback Form')
        self.assertIn('help make Day 2 even better',finding['explanation'])
        self.assertEqual(finding['links'],[{'url':'https://docs.google.com/forms/d/e/1FAIpQLSeSnC83-GUGYmsA9Ntybn9QRqJAPW4y4OFbEtI25VIYK9eg3g/viewform?usp=dialog','label':'Open feedback form ↗'}])
        self.assertEqual(finding['sources'][0]['text'],parse_messages(message)[0]['text'])
        self.assertEqual(finding['sources'][0]['sender'],'Maya')
        self.assertEqual(finding['sources'][0]['timestamp'],'10/7/26, 5:14:39 PM')
        self.assertNotEqual(finding['priority'],'URGENT')
    def test_multiple_links_keep_each_exact_url_and_context_label(self):
        text=('10/09/26, 9:00 AM - Jo: Please complete the registration form: https://forms.gle/AbC123 '
              'and view the project document: https://docs.google.com/document/d/XYZ/edit')
        finding=analyze(text)['categories']['IMPORTANT'][0]
        self.assertEqual(finding['links'],[
            {'url':'https://forms.gle/AbC123','label':'Open registration form ↗'},
            {'url':'https://docs.google.com/document/d/XYZ/edit','label':'View document ↗'}])
        self.assertEqual(finding['sources'][0]['text'],parse_messages(text)[0]['text'])
    def test_url_split_across_lines_is_joined_without_changing_other_source_text(self):
        url='https://docs.google.com/forms/d/e/abc123/viewform?usp=dialog'
        split='https://docs.google.com/forms/d/e/\nabc123/viewform?usp=dialog'
        text='10/09/26, 9:00 AM - Jo: Please fill out this feedback form: '+split
        finding=analyze(text)['categories']['IMPORTANT'][0]
        self.assertEqual(finding['links'][0]['url'],url)
        self.assertEqual(finding['sources'][0]['text'],parse_messages(text)[0]['text'])
    def test_linkless_announcement_is_fyi_with_information_heading(self):
        text='10/09/26, 9:00 AM - Jo: The workshop includes an AI scavenger hunt with prizes.'
        finding=analyze(text)['categories']['FYI'][0]
        self.assertEqual(finding['title'],'AI scavenger hunt announcement')
        self.assertEqual(finding['explanation'],'The workshop includes an AI scavenger hunt with prizes.')
        self.assertEqual(finding['links'],[])
    def test_explicit_deadline_is_in_description_and_not_made_urgent_by_tone(self):
        text='10/09/26, 9:00 AM - Jo: Please submit the report by 5 PM Friday! 🎉'
        finding=analyze(text)['categories']['IMPORTANT'][0]
        self.assertEqual(finding['title'],'Submit the report')
        self.assertIn('by 5 PM Friday',finding['explanation'])
        self.assertNotEqual(finding['priority'],'URGENT')
    def test_topic_groups_multiple_registrations_with_distinct_deadlines(self):
        result=analyze("10/09/26, 9:00 AM - Jo: Register for ABC ID today.\n10/09/26, 9:01 AM - Mo: Register for workshop by 12 October 2026.")
        items=[f for p in result['categories'].values() for f in p if f['topic']=='Registrations & Forms']
        self.assertEqual(len(items),2)
        self.assertNotEqual(items[0]['deadline'],items[1]['deadline'])
    def test_assignments_group_by_topic_but_keep_distinct_items(self):
        result=analyze("10/09/26, 9:00 AM - Jo: Complete Module 2 by Friday.\n10/09/26, 9:01 AM - Mo: Submit the CAED assignment.")
        items=[f for p in result['categories'].values() for f in p if f['topic']=='Assignments & Submissions']
        self.assertEqual(len(items),2)
    def test_duplicate_assignment_reminders_consolidate_evidence(self):
        result=analyze("10/09/26, 9:00 AM - Jo: Please complete Module 2.\n10/09/26, 9:01 AM - Mo: Complete Module 2.")
        items=[f for p in result['categories'].values() for f in p if f['topic']=='Assignments & Submissions']
        self.assertEqual(len(items),1); self.assertEqual(len(items[0]['sources']),2)
    def test_semantically_equivalent_assignment_titles_consolidate(self):
        result=analyze("10/09/26, 9:00 AM - Jo: Complete Module 2.\n10/09/26, 9:01 AM - Mo: Submit Module 2 assignment.")
        items=[f for p in result['categories'].values() for f in p if f['topic']=='Assignments & Submissions']
        self.assertEqual(len(items),1); self.assertEqual(len(items[0]['sources']),2)
    def test_similar_assignments_remain_separate(self):
        result=analyze("10/09/26, 9:00 AM - Jo: Complete Module 2.\n10/09/26, 9:01 AM - Mo: Complete Module 3.")
        items=[f for p in result['categories'].values() for f in p if f['topic']=='Assignments & Submissions']
        self.assertEqual(len(items),2)
    def test_relative_deadline_uses_message_date(self):
        result=analyze("[13/10/26, 9:00 AM] Jo: Please submit the assignment by tomorrow.")
        item=result['categories']['URGENT'][0]
        self.assertIn('tomorrow (14 October 2026)',item['deadline'])
    def test_weekday_deadline_is_resolved_from_message_timestamp(self):
        result=analyze("[13/10/26, 9:00 AM] Jo: Please submit the assignment by Friday.")
        item=result['categories']['IMPORTANT'][0]
        self.assertIn('Friday (16 October 2026)',item['deadline'])
    def test_ambiguous_relative_date_is_not_promoted_to_urgent(self):
        result=analyze("10/09/26, 9:00 AM - Jo: Please submit the assignment today.")
        self.assertEqual(len(result['categories']['IMPORTANT']),1)
        self.assertTrue(result['categories']['IMPORTANT'][0]['deadline'].startswith('Not specified'))
        self.assertIn('message date ambiguous',result['categories']['IMPORTANT'][0]['deadline'])
    def test_missing_deadline_is_not_invented(self):
        item=analyze("10/09/26, 9:00 AM - Jo: Please submit the assignment.")['categories']['IMPORTANT'][0]
        self.assertEqual(item['deadline'],'Not specified')
    def test_homework_question_is_not_classified_as_completed_task(self):
        item=analyze("10/09/26, 9:00 AM - Jo: How do I solve this homework?")['categories']['IMPORTANT'][0]
        self.assertEqual(item['topic'],'Homework & Doubts'); self.assertEqual(item['kind'],'question')
    def test_numbered_homework_question_links_later_answer(self):
        result=analyze("10/09/26, 9:00 AM - Jo: Can someone explain question 3?\n10/09/26, 9:05 AM - Mo: For question 3, use the quadratic formula.")
        item=result['categories']['IMPORTANT'][0]
        self.assertEqual(item['kind'],'question'); self.assertEqual(len(item['sources']),2)
        self.assertIn('appears to answer',item['explanation'])
    def test_item_retains_multiple_links_and_sources(self):
        result=analyze("10/09/26, 9:00 AM - Jo: Please register for the workshop: https://example.com/a\n10/09/26, 9:01 AM - Mo: Register for the workshop: https://example.com/b")
        items=[f for p in result['categories'].values() for f in p if f['topic']=='Registrations & Forms']
        self.assertTrue(any(len(f['sources'])==2 and len(f['links'])==2 for f in items))

class AnalysisHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app)
    def post(self,text):
        response=self.client.post('/api/analyze',json={'text':text})
        return response.status_code,response.json()
    def test_72343_character_unicode_chat_completes_and_links_exact_source(self):
        header='[10/5/26, 4:08:33 PM] - Maya: '
        prefix='Please send the email ID today. '
        text=header+prefix+(chr(233)*(72343-len(header)-len(prefix)))
        self.assertEqual(len(text),72343)
        status,result=self.post(text)
        self.assertEqual(status,200)
        source=result['categories']['IMPORTANT'][0]['sources'][0]
        self.assertEqual(source['text'],text[len(header):])
        self.assertEqual(source['sender'],'Maya')
    def test_empty_input_returns_actionable_client_error(self):
        status,result=self.post('')
        self.assertEqual(status,400)
        self.assertIn('non-empty',result['error'])
    def test_malformed_json_returns_client_error(self):
        response=self.client.post('/api/analyze',content='{',headers={'content-type':'application/json'})
        self.assertEqual(response.status_code,400)
        self.assertIn('Invalid request',response.json()['error'])
    def test_conversation_over_character_limit_is_rejected(self):
        response=self.client.post('/api/analyze',json={'text':'x'*1_000_001})
        self.assertEqual(response.status_code,413)
    def test_oversized_http_body_is_rejected_before_analysis(self):
        response=self.client.post('/api/analyze',content=b' '*8_100_001,headers={'content-type':'application/json'})
        self.assertEqual(response.status_code,413)
    def test_api_health_and_static_pwa_assets_are_available(self):
        self.assertEqual(self.client.get('/api/health').json(),{'status':'ok'})
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/manifest.webmanifest').status_code,200)
        self.assertEqual(self.client.get('/sw.js').status_code,200)
    def test_invalid_response_evidence_fails_validation(self):
        text='10/09/26, 9:00 AM - Jo: Register for the workshop: https://example.com/form'
        result=analyze(text)
        result['categories']['IMPORTANT'][0]['links'][0]['url']='https://bad.example/fake'
        with self.assertRaises(EvidenceValidationError):
            validate_analysis_evidence(result,text)

if __name__=='__main__': unittest.main()
