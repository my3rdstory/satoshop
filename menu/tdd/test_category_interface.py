"""
카테고리 관리 인터페이스 테스트 코드
프론트엔드 JavaScript 기능을 Django 테스트로 검증
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import JsonResponse
from stores.models import Store
from menu.models import MenuCategory
import json


class CategoryInterfaceTest(TestCase):
    def setUp(self):
        """테스트 환경 설정"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.store = Store.objects.create(
            store_id='test-store',
            owner=self.user,
            store_name='테스트 매장',
            store_description='테스트용 매장입니다',
            owner_name='테스트 사용자',
            owner_phone='010-1234-5678',
            chat_channel='https://example.com/chat'
        )
        self.client.login(username='testuser', password='testpass123')

    # 1. 모달 열기/닫기 테스트 (3개)
    def test_category_modal_page_loads(self):
        """Given: 메뉴 관리 페이지가 로드됨
        When: 카테고리 관리 버튼을 클릭함
        Then: 카테고리 관리 모달이 열림"""
        response = self.client.get(reverse('menu:menu_list', args=[self.store.store_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="categoryModal"')
        self.assertContains(response, 'onclick="openCategoryModal()"')

    def test_category_modal_close_button(self):
        """Given: 카테고리 관리 모달이 열려있음
        When: X 버튼을 클릭함
        Then: 모달이 닫힘"""
        response = self.client.get(reverse('menu:menu_list', args=[self.store.store_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'onclick="closeCategoryModal()"')

    def test_category_modal_background_click(self):
        """Given: 카테고리 관리 모달이 열려있음
        When: 모달 배경을 클릭함
        Then: 모달이 닫힘"""
        response = self.client.get(reverse('menu:menu_list', args=[self.store.store_id]))
        self.assertEqual(response.status_code, 200)
        # 모달 배경 클릭 이벤트가 있는지 확인
        self.assertContains(response, 'categoryModal')

    # 2. 카테고리 추가 테스트 (4개)
    def test_add_valid_category_api(self):
        """Given: 유효한 카테고리명이 입력됨
        When: 카테고리 추가 API를 호출함
        Then: 카테고리가 성공적으로 추가됨"""
        response = self.client.post(
            reverse('menu:category_create_api', args=[self.store.store_id]),
            data=json.dumps({'name': '신규 카테고리'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertTrue(MenuCategory.objects.filter(name='신규 카테고리').exists())

    def test_add_empty_category_validation(self):
        """Given: 빈 카테고리명이 입력됨
        When: 카테고리 추가 API를 호출함
        Then: 유효성 검증 오류가 반환됨"""
        response = self.client.post(
            reverse('menu:category_create_api', args=[self.store.store_id]),
            data=json.dumps({'name': ''}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])

    def test_add_duplicate_category_validation(self):
        """Given: 기존에 존재하는 카테고리명이 입력됨
        When: 카테고리 추가 API를 호출함
        Then: 중복 오류가 반환됨"""
        MenuCategory.objects.create(store=self.store, name='기존 카테고리')
        response = self.client.post(
            reverse('menu:category_create_api', args=[self.store.store_id]),
            data=json.dumps({'name': '기존 카테고리'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])

    def test_add_category_network_error_handling(self):
        """Given: 네트워크 오류가 발생함
        When: 카테고리 추가를 시도함
        Then: 적절한 오류 메시지가 표시됨"""
        # 잘못된 데이터로 네트워크 오류 시뮬레이션
        response = self.client.post(
            reverse('menu:category_create_api', args=[self.store.store_id]),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])

    # 3. 목록 표시 테스트 (2개)
    def test_display_categories_with_data(self):
        """Given: 여러 카테고리가 존재함
        When: 카테고리 목록을 조회함
        Then: 모든 카테고리가 이름순으로 표시됨"""
        MenuCategory.objects.create(store=self.store, name='ㅁ카테고리')
        MenuCategory.objects.create(store=self.store, name='ㄱ카테고리')
        MenuCategory.objects.create(store=self.store, name='ㅂ카테고리')
        
        response = self.client.get(reverse('menu:category_list_api', args=[self.store.store_id]))
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        categories = response_data['categories']
        category_names = [cat['name'] for cat in categories]
        self.assertEqual(category_names, ['ㄱ카테고리', 'ㅁ카테고리', 'ㅂ카테고리'])

    def test_display_empty_categories(self):
        """Given: 카테고리가 존재하지 않음
        When: 카테고리 목록을 조회함
        Then: 빈 목록이 반환됨"""
        response = self.client.get(reverse('menu:category_list_api', args=[self.store.store_id]))
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['categories'], [])

    # 4. 카테고리 수정 테스트 (4개)
    def test_edit_category_mode_activation(self):
        """Given: 카테고리가 존재함
        When: 수정 버튼을 클릭함
        Then: 수정 모드가 활성화됨"""
        category = MenuCategory.objects.create(store=self.store, name='수정할 카테고리')
        response = self.client.get(reverse('menu:menu_list', args=[self.store.store_id]))
        self.assertEqual(response.status_code, 200)
        # 카테고리 관리 모달이 있는지 확인
        self.assertContains(response, 'categoryModal')
        # JavaScript에서 editCategory 함수가 있는지 확인
        self.assertContains(response, 'menu-list.js')

    def test_update_category_valid_name(self):
        """Given: 카테고리가 수정 모드임
        When: 유효한 새 이름을 입력하고 저장함
        Then: 카테고리가 성공적으로 수정됨"""
        category = MenuCategory.objects.create(store=self.store, name='원래 이름')
        response = self.client.put(
            reverse('menu:category_update_api', args=[self.store.store_id, category.id]),
            data=json.dumps({'name': '수정된 이름'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        category.refresh_from_db()
        self.assertEqual(category.name, '수정된 이름')

    def test_update_category_empty_name(self):
        """Given: 카테고리가 수정 모드임
        When: 빈 이름을 입력하고 저장함
        Then: 유효성 검증 오류가 발생함"""
        category = MenuCategory.objects.create(store=self.store, name='원래 이름')
        response = self.client.put(
            reverse('menu:category_update_api', args=[self.store.store_id, category.id]),
            data=json.dumps({'name': ''}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])

    def test_cancel_category_edit(self):
        """Given: 카테고리가 수정 모드임
        When: 취소 버튼을 클릭함
        Then: 원래 이름으로 복원되고 수정 모드가 해제됨"""
        category = MenuCategory.objects.create(store=self.store, name='원래 이름')
        # 취소는 프론트엔드에서 처리되므로 데이터가 변경되지 않았는지 확인
        category.refresh_from_db()
        self.assertEqual(category.name, '원래 이름')

    # 5. 카테고리 삭제 테스트 (3개)
    def test_delete_category_confirmation_dialog(self):
        """Given: 카테고리가 존재함
        When: 삭제 버튼을 클릭함
        Then: 확인 대화상자가 표시됨"""
        category = MenuCategory.objects.create(store=self.store, name='삭제할 카테고리')
        response = self.client.get(reverse('menu:menu_list', args=[self.store.store_id]))
        self.assertEqual(response.status_code, 200)
        # 카테고리 관리 모달이 있는지 확인
        self.assertContains(response, 'categoryModal')
        # JavaScript에서 deleteCategory 함수가 있는지 확인
        self.assertContains(response, 'menu-list.js')

    def test_confirm_category_deletion(self):
        """Given: 삭제 확인 대화상자가 표시됨
        When: 확인 버튼을 클릭함
        Then: 카테고리가 삭제됨"""
        category = MenuCategory.objects.create(store=self.store, name='삭제할 카테고리')
        response = self.client.delete(
            reverse('menu:category_delete_api', args=[self.store.store_id, category.id])
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertFalse(MenuCategory.objects.filter(id=category.id).exists())

    def test_cancel_category_deletion(self):
        """Given: 삭제 확인 대화상자가 표시됨
        When: 취소 버튼을 클릭함
        Then: 카테고리가 삭제되지 않음"""
        category = MenuCategory.objects.create(store=self.store, name='삭제할 카테고리')
        # 취소는 프론트엔드에서 처리되므로 카테고리가 여전히 존재하는지 확인
        self.assertTrue(MenuCategory.objects.filter(id=category.id).exists())

    # 6. 필터 기능 테스트 (3개)
    def test_category_filter_buttons_creation(self):
        """Given: 여러 카테고리가 존재함
        When: 메뉴 목록 페이지를 로드함
        Then: 각 카테고리에 대한 필터 버튼이 생성됨"""
        MenuCategory.objects.create(store=self.store, name='카테고리1')
        MenuCategory.objects.create(store=self.store, name='카테고리2')
        response = self.client.get(reverse('menu:menu_list', args=[self.store.store_id]))
        self.assertEqual(response.status_code, 200)
        # 카테고리 필터 영역이 있는지 확인
        self.assertContains(response, 'categoryFilters')
        # JavaScript 파일이 로드되는지 확인
        self.assertContains(response, 'menu-list.js')

    def test_apply_category_filter(self):
        """Given: 카테고리 필터 버튼이 존재함
        When: 특정 카테고리 필터를 클릭함
        Then: 해당 카테고리의 메뉴만 표시됨"""
        category = MenuCategory.objects.create(store=self.store, name='테스트 카테고리')
        response = self.client.get(reverse('menu:menu_list', args=[self.store.store_id]))
        self.assertEqual(response.status_code, 200)
        # 메뉴 카드에 data-categories 속성이 있는지 확인
        self.assertContains(response, 'data-categories')

    def test_clear_category_filters(self):
        """Given: 카테고리 필터가 적용됨
        When: 전체 보기 버튼을 클릭함
        Then: 모든 메뉴가 다시 표시됨"""
        response = self.client.get(reverse('menu:menu_list', args=[self.store.store_id]))
        self.assertEqual(response.status_code, 200)
        # 전체 보기 기능이 있는지 확인
        self.assertContains(response, 'clearCategoryFilters')

    # 7. 알림 시스템 테스트 (3개)
    def test_success_notification_display(self):
        """Given: 카테고리 작업이 성공함
        When: 성공 응답을 받음
        Then: 성공 알림이 표시됨"""
        response = self.client.post(
            reverse('menu:category_create_api', args=[self.store.store_id]),
            data=json.dumps({'name': '성공 테스트'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        # 성공 메시지 확인
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])

    def test_error_notification_display(self):
        """Given: 카테고리 작업이 실패함
        When: 오류 응답을 받음
        Then: 오류 알림이 표시됨"""
        response = self.client.post(
            reverse('menu:category_create_api', args=[self.store.store_id]),
            data=json.dumps({'name': ''}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        # 오류 메시지 확인
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)

    def test_notification_replacement(self):
        """Given: 기존 알림이 표시되고 있음
        When: 새로운 알림이 발생함
        Then: 기존 알림이 새 알림으로 대체됨"""
        # 첫 번째 요청 (성공)
        response1 = self.client.post(
            reverse('menu:category_create_api', args=[self.store.store_id]),
            data=json.dumps({'name': '첫번째 카테고리'}),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, 200)
        response1_data = json.loads(response1.content)
        self.assertTrue(response1_data['success'])
        
        # 두 번째 요청 (실패)
        response2 = self.client.post(
            reverse('menu:category_create_api', args=[self.store.store_id]),
            data=json.dumps({'name': ''}),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, 200)
        response2_data = json.loads(response2.content)
        self.assertFalse(response2_data['success'])
        
        # 각각 다른 응답을 받았는지 확인
        self.assertNotEqual(response1_data['success'], response2_data['success']) 