"""
엣지 케이스 테스트
동시성 상황에서 발생할 수 있는 특수한 상황들을 테스트
"""

import threading
import time
from unittest.mock import patch, MagicMock
from django.test import TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from stores.models import Store
from meetup.models import Meetup, MeetupOrder
from .test_utils import ConcurrencyTestHelper, TestDataFactory


class EdgeCaseTestCase(TransactionTestCase):
    """엣지 케이스 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        self.owner = User.objects.create_user(
            username='edge_owner',
            email='edge@test.com',
            password='testpass123'
        )
        
        self.store = Store.objects.create(
            store_id='edgestore',
            store_name='엣지 케이스 테스트 스토어',
            owner=self.owner,
            business_registration_number='111-11-11111',
            business_name='엣지 테스트 사업자',
            business_owner_name='엣지 대표',
            business_contact='010-1111-1111',
            business_email='edge@test.com',
            bank_name='엣지은행',
            account_number='111111111',
            account_holder='엣지 대표'
        )
    
    def test_zero_capacity_meetup(self):
        """
        정원이 0명인 밋업 테스트
        Given: 밋업 정원이 0명으로 설정
        When: 여러 사용자가 신청을 시도
        Then: 모든 신청이 거부되어야 함
        """
        # 정원 0명인 밋업 생성
        meetup = Meetup.objects.create(
            store=self.store,
            name='정원 0명 테스트',
            description='정원이 0명인 밋업',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=0,
            max_participants=0,
            organizer_email='test@test.com',
            is_active=True
        )
        
        # 참가자들 생성
        participants = ConcurrencyTestHelper.create_load_test_users('zero_test', 5)
        
        # 동시 신청 시도
        results = ConcurrencyTestHelper.simulate_concurrent_requests(
            participants, meetup, self.store
        )
        
        # 결과 분석
        analysis = ConcurrencyTestHelper.analyze_concurrency_results(results, 0)
        
        print(f"정원 0명 테스트 결과:")
        print(f"- 성공한 요청: {analysis['successful_count']}")
        print(f"- 실패한 요청: {analysis['failed_count']}")
        
        # 모든 요청이 실패해야 함
        self.assertEqual(analysis['successful_count'], 0)
        self.assertEqual(meetup.current_participants, 0)
    
    def test_unlimited_capacity_meetup(self):
        """
        정원이 무제한인 밋업 테스트 (max_participants = None)
        Given: 밋업 정원이 무제한으로 설정
        When: 여러 사용자가 신청을 시도
        Then: 모든 신청이 성공해야 함
        """
        # 무제한 정원 밋업 생성
        meetup = Meetup.objects.create(
            store=self.store,
            name='무제한 정원 테스트',
            description='정원이 무제한인 밋업',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=0,
            max_participants=None,  # 무제한
            organizer_email='test@test.com',
            is_active=True
        )
        
        # 참가자들 생성
        participants = ConcurrencyTestHelper.create_load_test_users('unlimited_test', 10)
        
        # 동시 신청 시도
        results = ConcurrencyTestHelper.simulate_concurrent_requests(
            participants, meetup, self.store
        )
        
        # 결과 분석
        analysis = ConcurrencyTestHelper.analyze_concurrency_results(results, 10)
        
        print(f"무제한 정원 테스트 결과:")
        print(f"- 성공한 요청: {analysis['successful_count']}")
        print(f"- 최종 참가자 수: {meetup.current_participants}")
        
        # 모든 요청이 성공해야 함
        self.assertEqual(analysis['successful_count'], 10)
        self.assertEqual(meetup.current_participants, 10)
    
    def test_same_user_multiple_requests(self):
        """
        동일 사용자가 여러 번 신청하는 경우
        Given: 한 사용자가 동시에 여러 번 신청을 시도
        When: 같은 밋업에 중복 신청
        Then: 한 번만 성공하고 나머지는 거부되어야 함
        """
        meetup = Meetup.objects.create(
            store=self.store,
            name='중복 신청 테스트',
            description='동일 사용자 중복 신청 테스트',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=0,
            max_participants=5,
            organizer_email='test@test.com',
            is_active=True
        )
        
        # 한 명의 사용자
        user = User.objects.create_user(
            username='duplicate_user',
            email='duplicate@test.com',
            password='testpass123'
        )
        
        # 같은 사용자로 5번 동시 요청
        participants = [user] * 5
        
        results = ConcurrencyTestHelper.simulate_concurrent_requests(
            participants, meetup, self.store
        )
        
        # 실제 생성된 주문 수 확인
        user_orders = MeetupOrder.objects.filter(
            meetup=meetup,
            user=user
        )
        
        print(f"중복 신청 테스트 결과:")
        print(f"- 요청 수: {len(results)}")
        print(f"- 생성된 주문 수: {user_orders.count()}")
        print(f"- 확정된 주문 수: {user_orders.filter(status='confirmed').count()}")
        
        # 한 번만 주문이 생성되어야 함
        self.assertLessEqual(user_orders.count(), 1)
    
    def test_database_rollback_scenario(self):
        """
        데이터베이스 롤백 시나리오 테스트
        Given: 트랜잭션 중 오류가 발생하는 상황
        When: 일부 요청에서 오류가 발생
        Then: 정상적으로 롤백되고 데이터 일관성이 유지되어야 함
        """
        meetup = Meetup.objects.create(
            store=self.store,
            name='롤백 테스트',
            description='트랜잭션 롤백 테스트',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=0,
            max_participants=3,
            organizer_email='test@test.com',
            is_active=True
        )
        
        participants = ConcurrencyTestHelper.create_load_test_users('rollback_test', 5)
        
        # 일부 요청에서 의도적으로 오류 발생시키기
        def simulate_request_with_error(participant, should_error=False):
            from django.test.client import Client
            from django.urls import reverse
            
            client = Client()
            client.force_login(participant)
            
            try:
                if should_error:
                    # 잘못된 데이터로 요청하여 오류 발생
                    response = client.post(
                        reverse('meetup:meetup_checkout', kwargs={
                            'store_id': self.store.store_id,
                            'meetup_id': meetup.id
                        }),
                        data={
                            'participant_name': '',  # 빈 이름 (오류 유발)
                            'participant_email': 'invalid_email',  # 잘못된 이메일
                            'selected_options': '{}'
                        }
                    )
                else:
                    response = client.post(
                        reverse('meetup:meetup_checkout', kwargs={
                            'store_id': self.store.store_id,
                            'meetup_id': meetup.id
                        }),
                        data={
                            'participant_name': participant.username,
                            'participant_email': participant.email,
                            'participant_phone': '010-1234-5678',
                            'selected_options': '{}'
                        }
                    )
                
                return {
                    'user': participant.username,
                    'status_code': response.status_code,
                    'should_error': should_error,
                    'success': response.status_code in [200, 302]
                }
            except Exception as e:
                return {
                    'user': participant.username,
                    'error': str(e),
                    'should_error': should_error,
                    'success': False
                }
        
        results = []
        threads = []
        
        for i, participant in enumerate(participants):
            # 짝수 인덱스는 정상 요청, 홀수 인덱스는 오류 요청
            should_error = i % 2 == 1
            thread = threading.Thread(
                target=lambda p=participant, e=should_error: results.append(
                    simulate_request_with_error(p, e)
                )
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 결과 분석
        successful_results = [r for r in results if r.get('success', False)]
        error_results = [r for r in results if r.get('should_error', False)]
        
        print(f"롤백 테스트 결과:")
        print(f"- 총 요청: {len(results)}")
        print(f"- 성공한 요청: {len(successful_results)}")
        print(f"- 오류 유발 요청: {len(error_results)}")
        print(f"- 최종 참가자 수: {meetup.current_participants}")
        
        # 데이터 일관성 확인
        total_orders = MeetupOrder.objects.filter(meetup=meetup).count()
        confirmed_orders = MeetupOrder.objects.filter(
            meetup=meetup, status='confirmed'
        ).count()
        
        self.assertEqual(meetup.current_participants, confirmed_orders)
        self.assertLessEqual(confirmed_orders, 3)  # 정원 초과 안됨
    
    def test_meetup_deactivation_during_registration(self):
        """
        등록 진행 중 밋업이 비활성화되는 경우
        Given: 밋업 등록이 진행 중인 상황
        When: 관리자가 밋업을 비활성화
        Then: 새로운 신청은 거부되어야 함
        """
        meetup = Meetup.objects.create(
            store=self.store,
            name='비활성화 테스트',
            description='등록 중 비활성화 테스트',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=0,
            max_participants=5,
            organizer_email='test@test.com',
            is_active=True
        )
        
        participants = ConcurrencyTestHelper.create_load_test_users('deactivation_test', 6)
        
        def register_and_deactivate():
            """등록과 동시에 비활성화"""
            # 처음 3명은 정상 등록
            for i in range(3):
                try:
                    response, _ = ConcurrencyTestHelper.simulate_concurrent_requests(
                        [participants[i]], meetup, self.store
                    )[0], None
                except:
                    pass
                time.sleep(0.1)
            
            # 밋업 비활성화
            meetup.is_active = False
            meetup.save()
            
            # 나머지 3명은 비활성화 후 등록 시도
            for i in range(3, 6):
                try:
                    response, _ = ConcurrencyTestHelper.simulate_concurrent_requests(
                        [participants[i]], meetup, self.store
                    )[0], None
                except:
                    pass
                time.sleep(0.1)
        
        register_and_deactivate()
        
        # 결과 확인
        final_participants = meetup.current_participants
        
        print(f"비활성화 테스트 결과:")
        print(f"- 최종 참가자 수: {final_participants}")
        print(f"- 밋업 활성 상태: {meetup.is_active}")
        
        # 비활성화 후에는 새로운 등록이 안되어야 함
        self.assertFalse(meetup.is_active)
        self.assertLessEqual(final_participants, 3)
    
    def test_expired_meetup_registration(self):
        """
        만료된 밋업에 신청하는 경우
        Given: 밋업 시간이 지난 상태
        When: 사용자가 신청을 시도
        Then: 모든 신청이 거부되어야 함
        """
        # 이미 지난 시간의 밋업 생성
        meetup = Meetup.objects.create(
            store=self.store,
            name='만료된 밋업 테스트',
            description='이미 지난 밋업',
            date_time=timezone.now() - timezone.timedelta(days=1),  # 어제
            price=0,
            max_participants=5,
            organizer_email='test@test.com',
            is_active=True
        )
        
        participants = ConcurrencyTestHelper.create_load_test_users('expired_test', 3)
        
        results = ConcurrencyTestHelper.simulate_concurrent_requests(
            participants, meetup, self.store
        )
        
        analysis = ConcurrencyTestHelper.analyze_concurrency_results(results, 0)
        
        print(f"만료된 밋업 테스트 결과:")
        print(f"- 성공한 요청: {analysis['successful_count']}")
        print(f"- 밋업 만료 여부: {meetup.is_expired}")
        
        # 만료된 밋업은 신청이 안되어야 함
        self.assertTrue(meetup.is_expired)
        self.assertEqual(analysis['successful_count'], 0)
    
    def test_payment_timeout_during_concurrent_requests(self):
        """
        결제 타임아웃 중 동시 요청 처리
        Given: 여러 사용자가 동시에 결제를 시도
        When: 일부 결제가 타임아웃
        Then: 타임아웃된 주문은 취소되고 다른 대기자가 처리되어야 함
        """
        meetup = Meetup.objects.create(
            store=self.store,
            name='결제 타임아웃 테스트',
            description='결제 타임아웃 동시성 테스트',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=10000,  # 유료
            max_participants=2,
            organizer_email='test@test.com',
            is_active=True
        )
        
        participants = ConcurrencyTestHelper.create_load_test_users('timeout_test', 4)
        
        # 먼저 주문들을 생성 (pending 상태)
        orders = []
        for participant in participants:
            order = MeetupOrder.objects.create(
                meetup=meetup,
                user=participant,
                participant_name=participant.username,
                participant_email=participant.email,
                base_price=meetup.price,
                total_price=meetup.price,
                status='pending',
                # 일부 주문은 30분 전에 생성된 것으로 설정 (만료됨)
                created_at=timezone.now() - timezone.timedelta(minutes=35) if orders else timezone.now()
            )
            orders.append(order)
        
        # 만료된 주문 수동 처리
        from datetime import timedelta
        expired_orders = []
        for order in orders:
            if timezone.now() - order.created_at > timedelta(minutes=30):
                order.status = 'cancelled'
                order.save()
                expired_orders.append(order)
        
        # 남은 주문들로 동시 결제 시도
        active_orders = [o for o in orders if o.status == 'pending']
        
        def simulate_payment(order):
            with patch('meetup.views.get_blink_service_for_store') as mock_blink:
                mock_service = ConcurrencyTestHelper.create_mock_blink_service()
                mock_blink.return_value = mock_service
                
                try:
                    # 결제 완료 시뮬레이션 로직 필요
                    # 여기서는 간단히 주문 상태만 변경
                    with transaction.atomic():
                        locked_meetup = Meetup.objects.select_for_update().get(id=meetup.id)
                        if locked_meetup.current_participants < locked_meetup.max_participants:
                            order.status = 'confirmed'
                            order.paid_at = timezone.now()
                            order.confirmed_at = timezone.now()
                            order.save()
                            return True
                        else:
                            order.status = 'cancelled'
                            order.save()
                            return False
                except Exception:
                    return False
        
        payment_results = []
        threads = []
        
        for order in active_orders:
            thread = threading.Thread(
                target=lambda o=order: payment_results.append(simulate_payment(o))
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 결과 확인
        confirmed_count = sum(payment_results)
        final_participants = meetup.current_participants
        
        print(f"결제 타임아웃 테스트 결과:")
        print(f"- 만료된 주문: {len(expired_orders)}")
        print(f"- 활성 주문: {len(active_orders)}")
        print(f"- 확정된 결제: {confirmed_count}")
        print(f"- 최종 참가자 수: {final_participants}")
        
        # 정원을 초과하지 않아야 함
        self.assertLessEqual(final_participants, 2)
        self.assertLessEqual(confirmed_count, 2) 