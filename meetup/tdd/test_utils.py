"""
테스트 유틸리티 함수들
동시성 테스트를 위한 헬퍼 함수들과 공통 기능들
"""

import time
import threading
from unittest.mock import patch, MagicMock
from django.test.client import Client
from django.urls import reverse
from django.utils import timezone
from meetup.models import MeetupOrder


class ConcurrencyTestHelper:
    """동시성 테스트 헬퍼 클래스"""
    
    @staticmethod
    def create_mock_blink_service(payment_status='paid'):
        """Mock Blink 서비스 생성"""
        mock_service = MagicMock()
        mock_service.check_invoice_status.return_value = {
            'success': True,
            'status': payment_status
        }
        mock_service.create_invoice.return_value = {
            'success': True,
            'payment_hash': 'test_hash_123',
            'payment_request': 'test_payment_request'
        }
        return mock_service
    
    @staticmethod
    def simulate_concurrent_requests(participants, meetup, store, request_type='checkout', delay=0):
        """
        동시 요청 시뮬레이션
        
        Args:
            participants: 참가자 리스트
            meetup: 밋업 객체
            store: 스토어 객체
            request_type: 'checkout' 또는 'payment'
            delay: 요청 간 지연 시간 (초)
        
        Returns:
            list: 각 요청의 결과
        """
        results = []
        threads = []
        
        def make_request(participant, index):
            if delay > 0:
                time.sleep(delay * index)
            
            try:
                client = Client()
                client.force_login(participant)
                
                if request_type == 'checkout':
                    response = client.post(
                        reverse('meetup:meetup_checkout', kwargs={
                            'store_id': store.store_id,
                            'meetup_id': meetup.id
                        }),
                        data={
                            'participant_name': participant.username,
                            'participant_email': participant.email,
                            'participant_phone': '010-1234-5678',
                            'selected_options': '{}'
                        }
                    )
                else:  # payment
                    # 결제 요청의 경우 이미 생성된 주문을 찾아서 처리
                    order = MeetupOrder.objects.filter(
                        meetup=meetup,
                        user=participant,
                        status='pending'
                    ).first()
                    
                    if order:
                        with patch('meetup.views.get_blink_service_for_store') as mock_blink:
                            mock_blink.return_value = ConcurrencyTestHelper.create_mock_blink_service()
                            response = client.post(
                                reverse('meetup:check_meetup_payment_status', kwargs={
                                    'store_id': store.store_id,
                                    'meetup_id': meetup.id,
                                    'order_id': order.id
                                })
                            )
                    else:
                        response = None
                
                results.append({
                    'user': participant.username,
                    'index': index,
                    'status_code': response.status_code if response else None,
                    'success': response.status_code in [200, 302] if response else False,
                    'timestamp': time.time(),
                    'response': response
                })
            except Exception as e:
                results.append({
                    'user': participant.username,
                    'index': index,
                    'error': str(e),
                    'success': False,
                    'timestamp': time.time()
                })
        
        # 스레드 생성 및 실행
        for i, participant in enumerate(participants):
            thread = threading.Thread(target=make_request, args=(participant, i))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 결과를 시간순으로 정렬
        results.sort(key=lambda x: x.get('timestamp', 0))
        return results
    
    @staticmethod
    def analyze_concurrency_results(results, expected_success_count):
        """
        동시성 테스트 결과 분석
        
        Args:
            results: 테스트 결과 리스트
            expected_success_count: 예상 성공 건수
        
        Returns:
            dict: 분석 결과
        """
        successful = [r for r in results if r.get('success', False)]
        failed = [r for r in results if not r.get('success', False)]
        errors = [r for r in results if 'error' in r]
        
        return {
            'total_requests': len(results),
            'successful_count': len(successful),
            'failed_count': len(failed),
            'error_count': len(errors),
            'success_rate': len(successful) / len(results) if results else 0,
            'expected_success_count': expected_success_count,
            'meets_expectation': len(successful) == expected_success_count,
            'successful_users': [r['user'] for r in successful],
            'failed_users': [r['user'] for r in failed],
            'error_messages': [r.get('error', '') for r in errors]
        }
    
    @staticmethod
    def create_load_test_users(base_name, count, start_index=0):
        """
        부하 테스트용 사용자 대량 생성
        
        Args:
            base_name: 사용자명 접두사
            count: 생성할 사용자 수
            start_index: 시작 인덱스
        
        Returns:
            list: 생성된 사용자 리스트
        """
        from django.contrib.auth.models import User
        
        users = []
        for i in range(start_index, start_index + count):
            user = User.objects.create_user(
                username=f'{base_name}{i}',
                email=f'{base_name}{i}@test.com',
                password='testpass123'
            )
            users.append(user)
        return users


class DatabaseLockTestHelper:
    """데이터베이스 락 테스트 헬퍼"""
    
    @staticmethod
    def test_select_for_update_behavior(meetup, participants):
        """
        SELECT FOR UPDATE 동작 테스트
        
        실제로 락이 제대로 동작하는지 확인
        """
        from django.db import transaction
        
        lock_acquisition_order = []
        lock_release_order = []
        
        def acquire_lock_and_process(participant, processing_time=0.1):
            try:
                with transaction.atomic():
                    # SELECT FOR UPDATE로 락 획득
                    locked_meetup = meetup.__class__.objects.select_for_update().get(
                        id=meetup.id
                    )
                    
                    # 락 획득 시점 기록
                    lock_acquisition_order.append({
                        'user': participant.username,
                        'timestamp': time.time(),
                        'current_participants': locked_meetup.current_participants
                    })
                    
                    # 처리 시간 시뮬레이션
                    time.sleep(processing_time)
                    
                    # 실제 주문 생성 (간단한 버전)
                    if locked_meetup.current_participants < locked_meetup.max_participants:
                        MeetupOrder.objects.create(
                            meetup=locked_meetup,
                            user=participant,
                            participant_name=participant.username,
                            participant_email=participant.email,
                            base_price=locked_meetup.price,
                            total_price=locked_meetup.price,
                            status='confirmed',
                            paid_at=timezone.now(),
                            confirmed_at=timezone.now()
                        )
                        success = True
                    else:
                        success = False
                    
                    # 락 해제 시점 기록
                    lock_release_order.append({
                        'user': participant.username,
                        'timestamp': time.time(),
                        'success': success
                    })
                    
                    return success
                    
            except Exception as e:
                lock_release_order.append({
                    'user': participant.username,
                    'timestamp': time.time(),
                    'error': str(e),
                    'success': False
                })
                return False
        
        # 동시에 락 획득 시도
        threads = []
        results = []
        
        for participant in participants:
            thread = threading.Thread(
                target=lambda p=participant: results.append(
                    acquire_lock_and_process(p)
                )
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        return {
            'lock_acquisition_order': lock_acquisition_order,
            'lock_release_order': lock_release_order,
            'successful_operations': sum(results),
            'total_operations': len(results)
        }


class PerformanceTestHelper:
    """성능 테스트 헬퍼"""
    
    @staticmethod
    def measure_response_time(func, *args, **kwargs):
        """함수 실행 시간 측정"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        return {
            'result': result,
            'execution_time': end_time - start_time,
            'start_time': start_time,
            'end_time': end_time
        }
    
    @staticmethod
    def run_performance_test(test_func, iterations=100):
        """성능 테스트 실행"""
        execution_times = []
        errors = []
        
        for i in range(iterations):
            try:
                measurement = PerformanceTestHelper.measure_response_time(test_func)
                execution_times.append(measurement['execution_time'])
            except Exception as e:
                errors.append(str(e))
        
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            min_time = min(execution_times)
            max_time = max(execution_times)
        else:
            avg_time = min_time = max_time = 0
        
        return {
            'iterations': iterations,
            'successful_runs': len(execution_times),
            'error_count': len(errors),
            'average_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'execution_times': execution_times,
            'errors': errors
        }


class TestDataFactory:
    """테스트 데이터 팩토리"""
    
    @staticmethod
    def create_meetup_with_orders(store, meetup_name, max_participants, confirmed_count=0, pending_count=0):
        """
        주문이 포함된 밋업 생성
        
        Args:
            store: 스토어 객체
            meetup_name: 밋업명
            max_participants: 최대 참가자 수
            confirmed_count: 확정된 주문 수
            pending_count: 대기 중인 주문 수
        
        Returns:
            tuple: (meetup, confirmed_orders, pending_orders)
        """
        from meetup.models import Meetup
        from django.contrib.auth.models import User
        
        # 밋업 생성
        meetup = Meetup.objects.create(
            store=store,
            name=meetup_name,
            description=f'{meetup_name} 설명',
            date_time=timezone.now() + timezone.timedelta(days=7),
            price=10000,
            max_participants=max_participants,
            organizer_email='test@test.com',
            is_active=True
        )
        
        confirmed_orders = []
        pending_orders = []
        
        # 확정된 주문 생성
        for i in range(confirmed_count):
            user = User.objects.create_user(
                username=f'confirmed_user_{i}',
                email=f'confirmed{i}@test.com',
                password='testpass123'
            )
            order = MeetupOrder.objects.create(
                meetup=meetup,
                user=user,
                participant_name=user.username,
                participant_email=user.email,
                base_price=meetup.price,
                total_price=meetup.price,
                status='confirmed',
                paid_at=timezone.now(),
                confirmed_at=timezone.now()
            )
            confirmed_orders.append(order)
        
        # 대기 중인 주문 생성
        for i in range(pending_count):
            user = User.objects.create_user(
                username=f'pending_user_{i}',
                email=f'pending{i}@test.com',
                password='testpass123'
            )
            order = MeetupOrder.objects.create(
                meetup=meetup,
                user=user,
                participant_name=user.username,
                participant_email=user.email,
                base_price=meetup.price,
                total_price=meetup.price,
                status='pending'
            )
            pending_orders.append(order)
        
        return meetup, confirmed_orders, pending_orders 