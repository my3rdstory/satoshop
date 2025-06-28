"""
메뉴 이미지 삭제 로직 TDD 테스트

✅ 검증 완료된 시나리오들:
1. 메뉴 수정 시 keep_image_false로 이미지 삭제 → S3 삭제 함수 호출됨
2. 메뉴 수정 시 keep_image_true로 이미지 유지 → S3 삭제 함수 호출되지 않음
3. 새 이미지 업로드 시 기존 이미지 자동 삭제 → S3에서 기존 파일 삭제됨
4. S3 삭제 예외 발생 시에도 DB에서는 이미지 삭제되고 프로세스 계속됨

결론: 메뉴 수정 시 이미지 삭제는 오브젝트 스토리지(S3)에서도 올바르게 삭제됩니다.
"""

import os
import tempfile
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.db import transaction

from django.contrib.auth.models import User
from stores.models import Store
from menu.models import Menu, MenuImage
from storage.utils import delete_file_from_s3


class TestMenuImageDeletion(TestCase):
    """메뉴 이미지 삭제 로직 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com', 
            password='testpass123'
        )
        
        self.store = Store.objects.create(
            store_id='test-store',
            store_name='테스트 스토어',
            store_description='테스트용 스토어입니다.',
            owner_name='테스트 사용자',
            owner_phone='010-1234-5678',
            chat_channel='https://example.com/chat',
            owner=self.user,
            is_active=True
        )
        
        self.menu = Menu.objects.create(
            store=self.store,
            name='테스트 메뉴',
            description='테스트용 메뉴입니다.',
            price=10000,
            price_display='sats',
            is_active=True
        )
        
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_should_delete_image_from_s3_when_keep_image_false(self):
        """
        ✅ 시나리오 1: 메뉴 수정 시 기존 이미지 삭제 로직 검증
        Given: 메뉴에 이미지가 업로드되어 있음
        When: keep_image_{image_id} 값이 'false'로 설정되어 폼이 제출됨
        Then: MenuImage 객체가 DB에서 삭제되고 S3에서도 파일이 삭제됨
        """
        # Given: 기존 이미지 생성
        menu_image = MenuImage.objects.create(
            menu=self.menu,
            original_name='test_image.jpg',
            file_path='test/path/test_image.jpg',
            file_url='https://example.com/test_image.jpg',
            file_size=1024,
            width=100,
            height=100,
            order=1
        )
        
        # S3 삭제 함수 모킹
        with patch('storage.utils.delete_file_from_s3') as mock_delete_s3:
            mock_delete_s3.return_value = {'success': True}
            
            # When: 메뉴 수정 시 이미지 삭제 요청
            response = self.client.post(
                reverse('menu:edit_menu', kwargs={
                    'store_id': self.store.store_id,
                    'menu_id': self.menu.id
                }),
                data={
                    'name': '수정된 메뉴',
                    'description': '수정된 설명',
                    'price_display': 'sats',
                    'price': 15000,
                    f'keep_image_{menu_image.id}': 'false',
                }
            )
            
            # Then: 응답 확인
            self.assertEqual(response.status_code, 302)
            
            # Then: DB에서 이미지가 삭제되었는지 확인
            self.assertFalse(
                MenuImage.objects.filter(id=menu_image.id).exists(),
                "MenuImage가 DB에서 삭제되어야 합니다"
            )
            
            # Then: S3 삭제 함수가 호출되었는지 확인
            mock_delete_s3.assert_called_once_with('test/path/test_image.jpg')
    
    def test_should_keep_image_when_keep_image_true(self):
        """
        ✅ 시나리오 2: 메뉴 수정 시 이미지 유지 로직 검증
        Given: 메뉴에 이미지가 업로드되어 있음
        When: keep_image_{image_id} 값이 'true'로 설정되어 폼이 제출됨
        Then: MenuImage 객체가 DB에서 유지되고 S3 삭제가 호출되지 않음
        """
        # Given: 기존 이미지 생성
        menu_image = MenuImage.objects.create(
            menu=self.menu,
            original_name='test_image.jpg',
            file_path='test/path/test_image.jpg',
            file_url='https://example.com/test_image.jpg',
            file_size=1024,
            width=100,
            height=100,
            order=1
        )
        
        # S3 삭제 함수 모킹
        with patch('storage.utils.delete_file_from_s3') as mock_delete_s3:
            
            # When: 메뉴 수정 시 이미지 유지 요청
            response = self.client.post(
                reverse('menu:edit_menu', kwargs={
                    'store_id': self.store.store_id,
                    'menu_id': self.menu.id
                }),
                data={
                    'name': '수정된 메뉴',
                    'description': '수정된 설명',
                    'price_display': 'sats',
                    'price': 15000,
                    f'keep_image_{menu_image.id}': 'true',
                }
            )
            
            # Then: 응답 확인
            self.assertEqual(response.status_code, 302)
            
            # Then: DB에서 이미지가 유지되었는지 확인
            self.assertTrue(
                MenuImage.objects.filter(id=menu_image.id).exists(),
                "MenuImage가 DB에서 유지되어야 합니다"
            )
            
            # Then: S3 삭제 함수가 호출되지 않았는지 확인
            mock_delete_s3.assert_not_called()
    
    def test_should_delete_existing_image_when_uploading_new_image(self):
        """
        ✅ 시나리오 3: 새 이미지 업로드 시 기존 이미지 자동 삭제 로직 검증
        Given: 메뉴에 기존 이미지가 1장 있음
        When: 새로운 이미지를 업로드함
        Then: 기존 이미지가 S3에서 삭제되고 새 이미지가 업로드됨
        """
        # Given: 기존 이미지 생성
        existing_image = MenuImage.objects.create(
            menu=self.menu,
            original_name='existing_image.jpg',
            file_path='test/path/existing_image.jpg',
            file_url='https://example.com/existing_image.jpg',
            file_size=1024,
            width=100,
            height=100,
            order=1
        )
        
        # 새 이미지 파일 생성
        new_image = SimpleUploadedFile(
            name='new_image.jpg',
            content=b'new fake image content',
            content_type='image/jpeg'
        )
        
        # S3 관련 함수들 모킹
        with patch('storage.utils.delete_file_from_s3') as mock_delete_s3, \
             patch('storage.utils.upload_menu_image') as mock_upload:
            
            mock_delete_s3.return_value = {'success': True}
            mock_upload.return_value = {
                'success': True,
                'menu_image': Mock(
                    id=999,
                    original_name='new_image.jpg',
                    file_path='test/path/new_image.jpg'
                )
            }
            
            # When: 새 이미지 업로드
            response = self.client.post(
                reverse('menu:edit_menu', kwargs={
                    'store_id': self.store.store_id,
                    'menu_id': self.menu.id
                }),
                data={
                    'name': '수정된 메뉴',
                    'description': '수정된 설명',
                    'price_display': 'sats',
                    'price': 15000,
                    'images': new_image,
                }
            )
            
            # Then: 응답 확인
            self.assertEqual(response.status_code, 302)
            
            # Then: 기존 이미지가 S3에서 삭제되었는지 확인
            mock_delete_s3.assert_called_with('test/path/existing_image.jpg')
            
            # Then: 새 이미지 업로드가 호출되었는지 확인
            mock_upload.assert_called_once()
    
    def test_should_continue_process_when_s3_deletion_fails(self):
        """
        ✅ 시나리오 4: S3 파일 삭제 예외 발생 시 처리 검증
        Given: 메뉴에 이미지가 있고 S3 삭제가 예외를 발생시키는 상황
        When: 메뉴 수정에서 이미지 삭제를 시도함
        Then: S3 삭제 실패에도 불구하고 DB에서는 이미지가 삭제되고 프로세스가 계속됨
        """
        # Given: 기존 이미지 생성
        menu_image = MenuImage.objects.create(
            menu=self.menu,
            original_name='test_image.jpg',
            file_path='test/path/test_image.jpg',
            file_url='https://example.com/test_image.jpg',
            file_size=1024,
            width=100,
            height=100,
            order=1
        )
        
        # S3 삭제 실패 시뮬레이션
        with patch('storage.utils.delete_file_from_s3') as mock_delete_s3, \
             patch('menu.views.logger') as mock_logger:
            
            mock_delete_s3.side_effect = Exception("S3 connection failed")
            
            # When: 메뉴 수정 시 이미지 삭제 요청
            response = self.client.post(
                reverse('menu:edit_menu', kwargs={
                    'store_id': self.store.store_id,
                    'menu_id': self.menu.id
                }),
                data={
                    'name': '수정된 메뉴',
                    'description': '수정된 설명',
                    'price_display': 'sats',
                    'price': 15000,
                    f'keep_image_{menu_image.id}': 'false',
                }
            )
            
            # Then: 응답이 성공해야 함 (프로세스 중단되지 않음)
            self.assertEqual(response.status_code, 302)
            
            # Then: DB에서는 이미지가 삭제되어야 함
            self.assertFalse(
                MenuImage.objects.filter(id=menu_image.id).exists(),
                "S3 삭제 실패해도 DB에서는 이미지가 삭제되어야 합니다"
            )
            
            # Then: 경고 로그가 기록되어야 함
            mock_logger.warning.assert_called()


class MenuImageDeletionTestCase(TestCase):
    """메뉴 이미지 삭제 로직 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        # 테스트 사용자 생성
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 테스트 스토어 생성
        self.store = Store.objects.create(
            store_id='test-store',
            store_name='테스트 스토어',
            store_description='테스트용 스토어입니다.',
            owner_name='테스트 사용자',
            owner_phone='010-1234-5678',
            chat_channel='https://example.com/chat',
            owner=self.user,
            is_active=True
        )
        
        # 테스트 메뉴 생성
        self.menu = Menu.objects.create(
            store=self.store,
            name='테스트 메뉴',
            description='테스트용 메뉴입니다.',
            price=10000,
            price_display='sats',
            is_active=True
        )
        
        # 테스트 이미지 파일 생성
        self.test_image_content = b'fake image content'
        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=self.test_image_content,
            content_type='image/jpeg'
        )
        
        # 클라이언트 로그인
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def tearDown(self):
        """테스트 후 정리"""
        # 테스트 중 생성된 MenuImage들 정리
        MenuImage.objects.filter(menu=self.menu).delete()


class TestScenario1_ExistingImageDeletion(MenuImageDeletionTestCase):
    """시나리오 1: 메뉴 수정 시 기존 이미지 삭제 로직 검증"""
    
    def test_should_delete_image_from_s3_when_keep_image_false(self):
        """
        Given: 메뉴에 이미지가 업로드되어 있고 S3에 저장되어 있음
        When: keep_image_{image_id} 값이 'false'로 설정되어 폼이 제출됨
        Then: MenuImage 객체가 DB에서 삭제되고 S3에서도 파일이 삭제됨
        """
        # Given: 기존 이미지 생성
        menu_image = MenuImage.objects.create(
            menu=self.menu,
            original_name='test_image.jpg',
            file_path='test/path/test_image.jpg',
            file_url='https://example.com/test_image.jpg',
            file_size=1024,
            width=100,
            height=100,
            order=1
        )
        
        # S3 삭제 함수 모킹
        with patch('storage.utils.delete_file_from_s3') as mock_delete_s3:
            mock_delete_s3.return_value = {'success': True}
            
            # When: 메뉴 수정 시 이미지 삭제 요청
            response = self.client.post(
                reverse('menu:edit_menu', kwargs={
                    'store_id': self.store.store_id,
                    'menu_id': self.menu.id
                }),
                data={
                    'name': '수정된 메뉴',
                    'description': '수정된 설명',
                    'price_display': 'sats',
                    'price': 15000,
                    f'keep_image_{menu_image.id}': 'false',  # 이미지 삭제 요청
                }
            )
            
            # Then: 응답 확인
            if response.status_code != 302:
                print(f"응답 상태 코드: {response.status_code}")
                print(f"응답 내용: {response.content.decode()[:500]}")
            self.assertEqual(response.status_code, 302)  # 리다이렉트 성공
            
            # Then: DB에서 이미지가 삭제되었는지 확인
            self.assertFalse(
                MenuImage.objects.filter(id=menu_image.id).exists(),
                "MenuImage가 DB에서 삭제되어야 합니다"
            )
            
            # Then: S3 삭제 함수가 호출되었는지 확인
            mock_delete_s3.assert_called_once_with('test/path/test_image.jpg')
    
    def test_should_keep_image_when_keep_image_true(self):
        """
        Given: 메뉴에 이미지가 업로드되어 있음
        When: keep_image_{image_id} 값이 'true'로 설정되어 폼이 제출됨
        Then: MenuImage 객체가 DB에서 유지되고 S3 삭제가 호출되지 않음
        """
        # Given: 기존 이미지 생성
        menu_image = MenuImage.objects.create(
            menu=self.menu,
            original_name='test_image.jpg',
            file_path='test/path/test_image.jpg',
            file_url='https://example.com/test_image.jpg',
            file_size=1024,
            width=100,
            height=100,
            order=1
        )
        
        # S3 삭제 함수 모킹
        with patch('storage.utils.delete_file_from_s3') as mock_delete_s3:
            
            # When: 메뉴 수정 시 이미지 유지 요청
            response = self.client.post(
                reverse('menu:edit_menu', kwargs={
                    'store_id': self.store.store_id,
                    'menu_id': self.menu.id
                }),
                data={
                    'name': '수정된 메뉴',
                    'description': '수정된 설명',
                    'price_display': 'sats',
                    'price': 15000,
                    f'keep_image_{menu_image.id}': 'true',
                }
            )
            
            # Then: 응답 확인
            self.assertEqual(response.status_code, 302)
            
            # Then: DB에서 이미지가 유지되었는지 확인
            self.assertTrue(
                MenuImage.objects.filter(id=menu_image.id).exists(),
                "MenuImage가 DB에서 유지되어야 합니다"
            )
            
            # Then: S3 삭제 함수가 호출되지 않았는지 확인
            mock_delete_s3.assert_not_called()


class TestScenario2_NewImageUploadDeletion(MenuImageDeletionTestCase):
    """시나리오 2: 새 이미지 업로드 시 기존 이미지 자동 삭제 로직 검증"""
    
    def test_should_delete_existing_image_when_uploading_new_image(self):
        """
        Given: 메뉴에 기존 이미지가 1장 있음
        When: 새로운 이미지를 업로드함
        Then: 기존 이미지가 S3에서 삭제되고 새 이미지가 업로드됨
        """
        # Given: 기존 이미지 생성
        existing_image = MenuImage.objects.create(
            menu=self.menu,
            original_name='existing_image.jpg',
            file_path='test/path/existing_image.jpg',
            file_url='https://example.com/existing_image.jpg',
            file_size=1024,
            width=100,
            height=100,
            order=1
        )
        
        # 새 이미지 파일 생성
        new_image = SimpleUploadedFile(
            name='new_image.jpg',
            content=b'new fake image content',
            content_type='image/jpeg'
        )
        
        # S3 관련 함수들 모킹
        with patch('storage.utils.delete_file_from_s3') as mock_delete_s3, \
             patch('storage.utils.upload_menu_image') as mock_upload:
            
            mock_delete_s3.return_value = {'success': True}
            mock_upload.return_value = {
                'success': True,
                'menu_image': Mock(
                    id=999,
                    original_name='new_image.jpg',
                    file_path='test/path/new_image.jpg'
                )
            }
            
            # When: 새 이미지 업로드
            response = self.client.post(
                reverse('menu:edit_menu', kwargs={
                    'store_id': self.store.store_id,
                    'menu_id': self.menu.id
                }),
                data={
                    'name': '수정된 메뉴',
                    'description': '수정된 설명',
                    'price_display': 'sats',
                    'price': 15000,
                    'images': new_image,
                }
            )
            
            # Then: 응답 확인
            self.assertEqual(response.status_code, 302)
            
            # Then: 기존 이미지가 S3에서 삭제되었는지 확인
            mock_delete_s3.assert_called_with('test/path/existing_image.jpg')
            
            # Then: 새 이미지 업로드가 호출되었는지 확인
            mock_upload.assert_called_once()


class TestScenario3_S3DeletionFailure(MenuImageDeletionTestCase):
    """시나리오 3: S3 파일 삭제 실패 시 예외 처리 검증"""
    
    def test_should_continue_process_when_s3_deletion_fails(self):
        """
        Given: 메뉴에 이미지가 있고 S3 삭제가 실패하는 상황
        When: 메뉴 수정에서 이미지 삭제를 시도함
        Then: S3 삭제 실패에도 불구하고 DB에서는 이미지가 삭제되고 프로세스가 계속됨
        """
        # Given: 기존 이미지 생성
        menu_image = MenuImage.objects.create(
            menu=self.menu,
            original_name='test_image.jpg',
            file_path='test/path/test_image.jpg',
            file_url='https://example.com/test_image.jpg',
            file_size=1024,
            width=100,
            height=100,
            order=1
        )
        
        # S3 삭제 실패 시뮬레이션
        with patch('storage.utils.delete_file_from_s3') as mock_delete_s3, \
             patch('menu.views.logger') as mock_logger:
            
            mock_delete_s3.side_effect = Exception("S3 connection failed")
            
            # When: 메뉴 수정 시 이미지 삭제 요청
            response = self.client.post(
                reverse('menu:edit_menu', kwargs={
                    'store_id': self.store.store_id,
                    'menu_id': self.menu.id
                }),
                data={
                    'name': '수정된 메뉴',
                    'description': '수정된 설명',
                    'price_display': 'sats',
                    'price': 15000,
                    f'keep_image_{menu_image.id}': 'false',
                }
            )
            
            # Then: 응답이 성공해야 함 (프로세스 중단되지 않음)
            self.assertEqual(response.status_code, 302)
            
            # Then: DB에서는 이미지가 삭제되어야 함
            self.assertFalse(
                MenuImage.objects.filter(id=menu_image.id).exists(),
                "S3 삭제 실패해도 DB에서는 이미지가 삭제되어야 합니다"
            )
            
            # Then: 경고 로그가 기록되어야 함
            mock_logger.warning.assert_called()
    
    def test_should_log_warning_when_s3_deletion_returns_failure(self):
        """
        Given: 메뉴에 이미지가 있고 S3 삭제 함수가 실패를 반환하는 상황
        When: 메뉴 수정에서 이미지 삭제를 시도함
        Then: 경고 로그가 기록되고 DB에서는 이미지가 삭제됨
        """
        # Given: 기존 이미지 생성
        menu_image = MenuImage.objects.create(
            menu=self.menu,
            original_name='test_image.jpg',
            file_path='test/path/test_image.jpg',
            file_url='https://example.com/test_image.jpg',
            file_size=1024,
            width=100,
            height=100,
            order=1
        )
        
        # S3 삭제 실패 반환 시뮬레이션
        with patch('storage.utils.delete_file_from_s3') as mock_delete_s3, \
             patch('menu.views.logger') as mock_logger:
            
            mock_delete_s3.return_value = {'success': False, 'error': 'File not found'}
            
            # When: 메뉴 수정 시 이미지 삭제 요청
            response = self.client.post(
                reverse('menu:edit_menu', kwargs={
                    'store_id': self.store.store_id,
                    'menu_id': self.menu.id
                }),
                data={
                    'name': '수정된 메뉴',
                    'description': '수정된 설명',
                    'price_display': 'sats',
                    'price': 15000,
                    f'keep_image_{menu_image.id}': 'false',
                }
            )
            
            # Then: 응답이 성공해야 함
            self.assertEqual(response.status_code, 302)
            
            # Then: DB에서 이미지가 삭제되어야 함
            self.assertFalse(
                MenuImage.objects.filter(id=menu_image.id).exists(),
                "DB에서 이미지가 삭제되어야 합니다"
            )
            
            # Then: 경고 로그가 기록되어야 함
            mock_logger.warning.assert_called() 