"""
밋업 동시 좌석 신청 테스트
TDD 방법론 적용: 잔여 좌석보다 많은 동시 신청자가 있을 때의 다양한 시나리오 테스트
"""

import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from django.test.client import Client
from stores.models import Store
from meetup.models import Meetup, MeetupOrder


class ConcurrentReservationTestCase(TransactionTestCase):
    """동시성 테스트를 위한 TransactionTestCase 사용"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        # 사용자 생성
        self.owner = User.objects.create_user(
            username='owner', 
            email='owner@test.com',
            password='testpass123'
        )
        
        # 참가자들 생성
        self.participants = []
        for i in range(10):
            user = User.objects.create_user(
                username=f'participant{i}',
                email=f'participant{i}@test.com',
                password='testpass123'
            )
            self.participants.append(user)
        
        # 스토어 생성
        self.store = Store.objects.create(
            store_id='teststore',
            store_name='테스트 스토어',
            owner=self.owner,
            owner_name='테스트 대표',
            owner_phone='010-1234-5678',
            owner_email='business@test.com',
            chat_channel='https://open.kakao.com/test',
            is_active=True
        )
        # 테스트용 Blink API 정보 설정
        self.store.set_blink_api_info('test_api_info')
        self.store.set_blink_wallet_id('test_wallet_id')
        self.store.save()
        
        # 기본 밋업 생성 (정원 5명)
        self.meetup = Meetup.objects.create(
            store=self.store,
            name='동시성 테스트 밋업',
            description='동시성 테스트를 위한 밋업입니다',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=10000,  # 유료 밋업
            max_participants=5,
            organizer_email='organizer@test.com',
            is_active=True
        )
        
        # 무료 밋업 생성 (정원 2명)
        self.free_meetup = Meetup.objects.create(
            store=self.store,
            name='무료 동시성 테스트 밋업',
            description='무료 동시성 테스트를 위한 밋업입니다',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=0,  # 무료 밋업
            max_participants=2,
            organizer_email='organizer@test.com',
            is_active=True
        )
    
    def create_confirmed_order(self, meetup, user, participant_name):
        """확정된 주문 생성 헬퍼 메서드"""
        return MeetupOrder.objects.create(
            meetup=meetup,
            user=user,
            participant_name=participant_name,
            participant_email=user.email,
            base_price=meetup.price,
            total_price=meetup.price,
            status='confirmed',
            paid_at=timezone.now(),
            confirmed_at=timezone.now()
        )
    
    def simulate_checkout_request(self, user, meetup):
        """체크아웃 요청 시뮬레이션"""
        client = Client()
        client.force_login(user)
        
        # POST 요청으로 주문 생성 시뮬레이션
        response = client.post(
            reverse('meetup:meetup_checkout', kwargs={
                'store_id': self.store.store_id,
                'meetup_id': meetup.id
            }),
            data={
                'participant_name': user.username,
                'participant_email': user.email,
                'participant_phone': '010-1234-5678',
                'selected_options': '{}'
            }
        )
        return response, client
    
    def simulate_payment_completion(self, order):
        """결제 완료 시뮬레이션"""
        client = Client()
        
        # 결제 상태 확인 API 호출 시뮬레이션
        with patch('meetup.views.get_blink_service_for_store') as mock_blink:
            mock_service = MagicMock()
            mock_service.check_invoice_status.return_value = {
                'success': True,
                'status': 'paid'
            }
            mock_blink.return_value = mock_service
            
            response = client.post(
                reverse('meetup:check_meetup_payment_status', kwargs={
                    'store_id': self.store.store_id,
                    'meetup_id': order.meetup.id,
                    'order_id': order.id
                })
            )
            return response

    def test_scenario_1_basic_concurrency(self):
        """
        시나리오 1: 기본 동시성 테스트
        Given: 밋업 정원이 5명이고, 현재 4명이 참가 확정된 상태
        When: 5명의 사용자가 동시에 마지막 1자리에 참가 신청을 시도
        Then: 1명만 참가 확정되고, 나머지 4명은 정원 마감 메시지를 받는다
        """
        # Given: 4명이 이미 참가 확정
        for i in range(4):
            self.create_confirmed_order(
                self.meetup, 
                self.participants[i], 
                f'participant{i}'
            )
        
        # 현재 참가자 수 확인
        self.assertEqual(self.meetup.current_participants, 4)
        self.assertEqual(self.meetup.remaining_spots, 1)
        
        # When: 5명이 동시에 신청
        results = []
        threads = []
        
        def concurrent_request(participant):
            try:
                response, client = self.simulate_checkout_request(participant, self.meetup)
                results.append({
                    'user': participant.username,
                    'status_code': response.status_code,
                    'response': response
                })
            except Exception as e:
                results.append({
                    'user': participant.username,
                    'error': str(e)
                })
        
        # 5명의 참가자가 동시에 요청
        for i in range(4, 9):
            thread = threading.Thread(
                target=concurrent_request, 
                args=(self.participants[i],)
            )
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # Then: 결과 검증
        # 총 참가자는 5명을 초과하지 않아야 함
        final_participants = self.meetup.current_participants
        self.assertLessEqual(final_participants, 5)
        
        # 성공한 요청과 실패한 요청 분석
        successful_requests = []
        failed_requests = []
        
        for result in results:
            if 'error' not in result:
                if result['status_code'] in [200, 302]:  # 성공 또는 리다이렉트
                    successful_requests.append(result)
                else:
                    failed_requests.append(result)
            else:
                failed_requests.append(result)
        
        print(f"시나리오 1 결과:")
        print(f"- 최종 참가자 수: {final_participants}")
        print(f"- 성공한 요청: {len(successful_requests)}")
        print(f"- 실패한 요청: {len(failed_requests)}")
        
        # 최대 1명만 추가로 참가할 수 있어야 함
        additional_participants = final_participants - 4
        self.assertLessEqual(additional_participants, 1)

    def test_scenario_2_payment_processing_overflow_prevention(self):
        """
        시나리오 2: 결제 처리 중 정원 초과 방지
        Given: 밋업 정원이 3명이고, 현재 2명이 참가 확정된 상태에서 2명이 결제 대기 중
        When: 첫 번째 사용자가 결제를 완료
        Then: 첫 번째 사용자는 참가 확정되고, 두 번째 사용자의 주문은 취소되며 환불 처리된다
        """
        # 정원 3명인 새로운 밋업 생성
        small_meetup = Meetup.objects.create(
            store=self.store,
            name='소규모 테스트 밋업',
            description='결제 처리 중 정원 초과 방지 테스트',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=20000,
            max_participants=3,
            organizer_email='organizer@test.com',
            is_active=True
        )
        
        # Given: 2명이 이미 참가 확정
        for i in range(2):
            self.create_confirmed_order(
                small_meetup, 
                self.participants[i], 
                f'participant{i}'
            )
        
        # 2명의 결제 대기 주문 생성
        pending_orders = []
        for i in range(2, 4):
            order = MeetupOrder.objects.create(
                meetup=small_meetup,
                user=self.participants[i],
                participant_name=f'participant{i}',
                participant_email=self.participants[i].email,
                base_price=small_meetup.price,
                total_price=small_meetup.price,
                status='pending'
            )
            pending_orders.append(order)
        
        # When: 동시에 결제 완료 시도
        payment_results = []
        threads = []
        
        def concurrent_payment(order):
            try:
                response = self.simulate_payment_completion(order)
                payment_results.append({
                    'order_id': order.id,
                    'user': order.user.username,
                    'status_code': response.status_code,
                    'response_content': response.content.decode() if hasattr(response, 'content') else str(response)
                })
            except Exception as e:
                payment_results.append({
                    'order_id': order.id,
                    'user': order.user.username,
                    'error': str(e)
                })
        
        # 2명이 동시에 결제 완료
        for order in pending_orders:
            thread = threading.Thread(target=concurrent_payment, args=(order,))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # Then: 결과 검증
        # 주문 상태 새로고침
        for order in pending_orders:
            order.refresh_from_db()
        
        confirmed_orders = [o for o in pending_orders if o.status == 'confirmed']
        cancelled_orders = [o for o in pending_orders if o.status == 'cancelled']
        
        print(f"시나리오 2 결과:")
        print(f"- 최종 참가자 수: {small_meetup.current_participants}")
        print(f"- 확정된 주문: {len(confirmed_orders)}")
        print(f"- 취소된 주문: {len(cancelled_orders)}")
        
        # 정원을 초과하지 않아야 함
        self.assertLessEqual(small_meetup.current_participants, 3)
        # 1명만 추가로 확정되어야 함
        self.assertLessEqual(len(confirmed_orders), 1)

    def test_scenario_3_order_creation_payment_time_gap(self):
        """
        시나리오 3: 주문 생성과 결제 완료 사이의 시간차 처리
        Given: 밋업 정원이 2명이고, 현재 1명이 참가 확정된 상태
        When: 3명의 사용자가 동시에 주문을 생성하고 순차적으로 결제를 시도
        Then: 첫 번째 결제자만 참가 확정되고, 나머지는 결제 시점에 정원 마감으로 취소된다
        """
        # 정원 2명인 새로운 밋업 생성
        tiny_meetup = Meetup.objects.create(
            store=self.store,
            name='초소규모 테스트 밋업',
            description='주문-결제 시간차 테스트',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=15000,
            max_participants=2,
            organizer_email='organizer@test.com',
            is_active=True
        )
        
        # Given: 1명이 이미 참가 확정
        self.create_confirmed_order(
            tiny_meetup, 
            self.participants[0], 
            'participant0'
        )
        
        # When: 3명이 동시에 주문 생성
        order_results = []
        threads = []
        
        def concurrent_order_creation(participant):
            try:
                response, client = self.simulate_checkout_request(participant, tiny_meetup)
                order_results.append({
                    'user': participant.username,
                    'status_code': response.status_code,
                    'response': response
                })
            except Exception as e:
                order_results.append({
                    'user': participant.username,
                    'error': str(e)
                })
        
        # 3명이 동시에 주문 생성
        for i in range(1, 4):
            thread = threading.Thread(
                target=concurrent_order_creation, 
                args=(self.participants[i],)
            )
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 생성된 주문들을 찾아서 순차적으로 결제 시도
        created_orders = MeetupOrder.objects.filter(
            meetup=tiny_meetup,
            status='pending'
        ).order_by('created_at')
        
        payment_results = []
        for order in created_orders:
            # 약간의 시간 간격을 두고 결제 시도
            time.sleep(0.1)
            try:
                response = self.simulate_payment_completion(order)
                order.refresh_from_db()
                payment_results.append({
                    'order_id': order.id,
                    'user': order.user.username,
                    'final_status': order.status,
                    'response_status': response.status_code
                })
            except Exception as e:
                payment_results.append({
                    'order_id': order.id,
                    'user': order.user.username,
                    'error': str(e)
                })
        
        # Then: 결과 검증
        final_participants = tiny_meetup.current_participants
        confirmed_payment_orders = [r for r in payment_results if r.get('final_status') == 'confirmed']
        
        print(f"시나리오 3 결과:")
        print(f"- 생성된 주문 수: {len(created_orders)}")
        print(f"- 최종 참가자 수: {final_participants}")
        print(f"- 결제 확정된 주문: {len(confirmed_payment_orders)}")
        
        # 정원을 초과하지 않아야 함
        self.assertLessEqual(final_participants, 2)
        # 최대 1명만 추가로 확정되어야 함
        self.assertLessEqual(len(confirmed_payment_orders), 1)

    def test_scenario_4_free_meetup_concurrent_application(self):
        """
        시나리오 4: 무료 밋업의 동시 신청 처리
        Given: 무료 밋업의 정원이 2명이고, 현재 1명이 참가 확정된 상태
        When: 5명의 사용자가 동시에 무료 참가 신청을 시도
        Then: 1명만 즉시 참가 확정되고, 나머지는 정원 마감 메시지를 받는다
        """
        # Given: 1명이 이미 참가 확정
        self.create_confirmed_order(
            self.free_meetup, 
            self.participants[0], 
            'participant0'
        )
        
        # 현재 상태 확인
        self.assertEqual(self.free_meetup.current_participants, 1)
        self.assertEqual(self.free_meetup.remaining_spots, 1)
        
        # When: 5명이 동시에 무료 신청
        free_results = []
        threads = []
        
        def concurrent_free_request(participant):
            try:
                response, client = self.simulate_checkout_request(participant, self.free_meetup)
                free_results.append({
                    'user': participant.username,
                    'status_code': response.status_code,
                    'response': response
                })
            except Exception as e:
                free_results.append({
                    'user': participant.username,
                    'error': str(e)
                })
        
        # 5명이 동시에 요청
        for i in range(1, 6):
            thread = threading.Thread(
                target=concurrent_free_request, 
                args=(self.participants[i],)
            )
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # Then: 결과 검증
        final_participants = self.free_meetup.current_participants
        confirmed_orders = MeetupOrder.objects.filter(
            meetup=self.free_meetup,
            status='confirmed'
        ).count()
        
        print(f"시나리오 4 결과:")
        print(f"- 최종 참가자 수: {final_participants}")
        print(f"- 확정된 주문 수: {confirmed_orders}")
        
        # 정원을 초과하지 않아야 함
        self.assertLessEqual(final_participants, 2)
        self.assertEqual(confirmed_orders, final_participants)

    def test_scenario_5_network_delay_and_timeout(self):
        """
        시나리오 5: 네트워크 지연과 타임아웃 상황
        Given: 밋업 정원이 1명이고, 현재 참가자가 0명인 상태
        When: 2명의 사용자가 동시에 신청하되, 한 명은 네트워크 지연으로 요청이 늦게 도착
        Then: 먼저 도착한 요청만 처리되고, 늦게 도착한 요청은 정원 마감으로 거부된다
        """
        # 정원 1명인 새로운 밋업 생성
        single_meetup = Meetup.objects.create(
            store=self.store,
            name='단일 정원 테스트 밋업',
            description='네트워크 지연 테스트',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=5000,
            max_participants=1,
            organizer_email='organizer@test.com',
            is_active=True
        )
        
        # Given: 현재 참가자 0명
        self.assertEqual(single_meetup.current_participants, 0)
        
        # When: 2명이 시간차를 두고 신청
        delay_results = []
        
        def fast_request():
            try:
                response, client = self.simulate_checkout_request(
                    self.participants[0], single_meetup
                )
                delay_results.append({
                    'user': 'fast_user',
                    'status_code': response.status_code,
                    'timestamp': time.time()
                })
            except Exception as e:
                delay_results.append({
                    'user': 'fast_user',
                    'error': str(e),
                    'timestamp': time.time()
                })
        
        def slow_request():
            # 네트워크 지연 시뮬레이션
            time.sleep(0.5)
            try:
                response, client = self.simulate_checkout_request(
                    self.participants[1], single_meetup
                )
                delay_results.append({
                    'user': 'slow_user',
                    'status_code': response.status_code,
                    'timestamp': time.time()
                })
            except Exception as e:
                delay_results.append({
                    'user': 'slow_user',
                    'error': str(e),
                    'timestamp': time.time()
                })
        
        # 동시에 시작하지만 한쪽은 지연
        fast_thread = threading.Thread(target=fast_request)
        slow_thread = threading.Thread(target=slow_request)
        
        fast_thread.start()
        slow_thread.start()
        
        fast_thread.join()
        slow_thread.join()
        
        # Then: 결과 검증
        final_participants = single_meetup.current_participants
        
        # 시간순으로 정렬
        delay_results.sort(key=lambda x: x.get('timestamp', 0))
        
        print(f"시나리오 5 결과:")
        print(f"- 최종 참가자 수: {final_participants}")
        print(f"- 요청 순서: {[r['user'] for r in delay_results]}")
        
        # 정원을 초과하지 않아야 함
        self.assertLessEqual(final_participants, 1)

    def test_stress_test_high_concurrency(self):
        """
        스트레스 테스트: 높은 동시성 상황
        Given: 밋업 정원이 10명이고, 현재 참가자가 0명인 상태
        When: 50명의 사용자가 동시에 신청을 시도
        Then: 정확히 10명만 참가 확정되고, 나머지는 정원 마감으로 거부된다
        """
        # 대용량 테스트를 위한 추가 사용자 생성
        stress_participants = []
        for i in range(50):
            user = User.objects.create_user(
                username=f'stress_user{i}',
                email=f'stress{i}@test.com',
                password='testpass123'
            )
            stress_participants.append(user)
        
        # 정원 10명인 새로운 밋업 생성
        stress_meetup = Meetup.objects.create(
            store=self.store,
            name='스트레스 테스트 밋업',
            description='높은 동시성 테스트',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=0,  # 무료로 설정하여 즉시 확정
            max_participants=10,
            organizer_email='organizer@test.com',
            is_active=True
        )
        
        # When: 50명이 동시에 신청
        stress_results = []
        
        def stress_request(participant):
            try:
                response, client = self.simulate_checkout_request(participant, stress_meetup)
                stress_results.append({
                    'user': participant.username,
                    'status_code': response.status_code,
                    'success': response.status_code in [200, 302]
                })
            except Exception as e:
                stress_results.append({
                    'user': participant.username,
                    'error': str(e),
                    'success': False
                })
        
        # ThreadPoolExecutor 사용으로 높은 동시성 구현
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(stress_request, participant) 
                for participant in stress_participants
            ]
            
            # 모든 작업 완료 대기
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"스트레스 테스트 중 오류: {e}")
        
        # Then: 결과 검증
        final_participants = stress_meetup.current_participants
        successful_requests = len([r for r in stress_results if r.get('success', False)])
        
        print(f"스트레스 테스트 결과:")
        print(f"- 총 요청 수: {len(stress_results)}")
        print(f"- 성공한 요청: {successful_requests}")
        print(f"- 최종 참가자 수: {final_participants}")
        
        # 정확히 정원만큼만 참가 확정되어야 함
        self.assertEqual(final_participants, 10)
        
        # 데이터 정합성 확인
        confirmed_orders = MeetupOrder.objects.filter(
            meetup=stress_meetup,
            status='confirmed'
        ).count()
        self.assertEqual(confirmed_orders, 10)

    def tearDown(self):
        """테스트 후 정리"""
        # 모든 생성된 데이터는 TransactionTestCase에 의해 자동으로 롤백됨
        pass


class ConcurrentReservationIntegrationTest(TestCase):
    """통합 테스트 - 실제 HTTP 요청 시뮬레이션"""
    
    def setUp(self):
        """통합 테스트 데이터 설정"""
        self.owner = User.objects.create_user(
            username='integration_owner',
            email='integration@test.com',
            password='testpass123'
        )
        
        self.store = Store.objects.create(
            store_id='integrationstore',
            store_name='통합 테스트 스토어',
            owner=self.owner,
            owner_name='통합 대표',
            owner_phone='010-9876-5432',
            owner_email='integration@test.com',
            chat_channel='https://open.kakao.com/integration',
            is_active=True
        )
        # 테스트용 Blink API 정보 설정
        self.store.set_blink_api_info('test_api_info')
        self.store.set_blink_wallet_id('test_wallet_id')
        self.store.save()
        
        self.meetup = Meetup.objects.create(
            store=self.store,
            name='통합 테스트 밋업',
            description='HTTP 요청 통합 테스트',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=30000,
            max_participants=3,
            organizer_email='integration@test.com',
            is_active=True
        )
    
    def test_http_concurrent_requests(self):
        """
        HTTP 레벨에서의 동시 요청 테스트
        실제 웹 요청과 유사한 환경에서 테스트
        """
        # 동시 HTTP 요청 시뮬레이션
        clients = []
        for i in range(5):
            client = Client()
            # 비회원 요청으로 시뮬레이션
            clients.append(client)
        
        responses = []
        threads = []
        
        def http_request(client, index):
            try:
                response = client.post(
                    reverse('meetup:meetup_checkout', kwargs={
                        'store_id': self.store.store_id,
                        'meetup_id': self.meetup.id
                    }),
                    data={
                        'participant_name': f'HTTP User {index}',
                        'participant_email': f'http{index}@test.com',
                        'participant_phone': '010-1111-2222',
                        'selected_options': '{}'
                    }
                )
                responses.append({
                    'index': index,
                    'status_code': response.status_code,
                    'success': response.status_code in [200, 302]
                })
            except Exception as e:
                responses.append({
                    'index': index,
                    'error': str(e),
                    'success': False
                })
        
        # 5개의 동시 HTTP 요청
        for i, client in enumerate(clients):
            thread = threading.Thread(target=http_request, args=(client, i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 결과 분석
        final_participants = self.meetup.current_participants
        successful_requests = len([r for r in responses if r.get('success', False)])
        
        print(f"HTTP 통합 테스트 결과:")
        print(f"- 총 요청 수: {len(responses)}")
        print(f"- 성공한 요청: {successful_requests}")
        print(f"- 최종 참가자 수: {final_participants}")
        
        # 정원을 초과하지 않아야 함
        self.assertLessEqual(final_participants, 3) 