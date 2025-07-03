from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.cache import cache
import csv
import io
import uuid
import time

from ..models import Meetup, MeetupOrder


def update_progress(task_id, current, total, status, message=""):
    """진행 상황 업데이트"""
    progress_data = {
        'current': current,
        'total': total,
        'percentage': int((current / total) * 100) if total > 0 else 0,
        'status': status,
        'message': message,
        'timestamp': time.time()
    }
    cache.set(f'csv_progress_{task_id}', progress_data, timeout=300)  # 5분 timeout
    print(f"DEBUG: Progress updated - Task: {task_id}, Current: {current}, Total: {total}, Status: {status}, Message: {message}")


@staff_member_required
def get_progress(request, task_id):
    """진행 상황 조회 API"""
    progress_data = cache.get(f'csv_progress_{task_id}')
    if progress_data:
        return JsonResponse(progress_data)
    else:
        return JsonResponse({'error': 'Task not found'}, status=404)


@staff_member_required
def csv_upload_view(request, meetup_id):
    """CSV 파일로 참가자 일괄 추가 - 독립적인 뷰"""
    meetup = get_object_or_404(Meetup, id=meetup_id)
    
    if request.method == 'POST':
        print(f"DEBUG: CSV data POST request received for meetup {meetup_id}")
        print(f"DEBUG: POST data: {dict(request.POST)}")
        
        # 텍스트 영역에서 CSV 데이터 처리
        csv_text = request.POST.get('csv_data', '').strip()
        if not csv_text:
            print("DEBUG: No CSV data found")
            messages.error(request, 'CSV 데이터를 입력해주세요.')
            return redirect(request.get_full_path())
        
        # task_id 가져오기 (폼에서 전달받은 값 사용)
        task_id = request.POST.get('task_id', str(uuid.uuid4()))
        
        success_count = 0
        error_messages = []
        
        try:
            print("DEBUG: Starting CSV processing...")
            # 텍스트에서 CSV 데이터 읽기 (줄바꿈 문자 정규화)
            normalized_text = csv_text.replace('\r\n', '\n').replace('\r', '\n')
            csv_lines = [line.strip() for line in normalized_text.strip().split('\n') if line.strip()]
            total_lines = len(csv_lines)
            
            print(f"DEBUG: Total lines to process: {total_lines}")
            print(f"DEBUG: Lines: {csv_lines}")
            
            # 초기 진행 상황 설정
            update_progress(task_id, 0, total_lines, 'processing', '참가자 데이터 분석 중...')
            
            csv_data = csv.reader(io.StringIO(normalized_text))
            
            for row_num, row in enumerate(csv_data, start=1):
                print(f"DEBUG: Processing row {row_num}: {row}")
                
                # 진행 상황 업데이트
                update_progress(task_id, row_num - 1, total_lines, 'processing', f'{row_num}번째 참가자 처리 중...')
                
                if len(row) < 2:  # 최소 이름, 이메일 필요
                    print(f"DEBUG: Row {row_num} has insufficient columns: {len(row)}")
                    error_messages.append(f'행 {row_num}: 참가자명과 이메일은 필수입니다.')
                    continue
                
                participant_name = row[0].strip()
                participant_email = row[1].strip()
                participant_phone = row[2].strip() if len(row) > 2 else ''
                username = row[3].strip() if len(row) > 3 else ''
                
                print(f"DEBUG: Parsed data - Name: '{participant_name}', Email: '{participant_email}', Phone: '{participant_phone}', Username: '{username}'")
                
                if not participant_name or not participant_email:
                    print(f"DEBUG: Empty required fields - Name: '{participant_name}', Email: '{participant_email}'")
                    error_messages.append(f'행 {row_num}: 참가자명과 이메일은 필수입니다.')
                    continue
                
                # 이메일 중복 체크 (같은 밋업에서)
                existing_order = MeetupOrder.objects.filter(meetup=meetup, participant_email=participant_email).first()
                if existing_order:
                    print(f"DEBUG: Duplicate email found: {participant_email}")
                    error_messages.append(f'행 {row_num}: {participant_email}는 이미 등록된 참가자입니다.')
                    continue
                
                # 사용자 찾기 (있으면 연결)
                user = None
                if username:
                    try:
                        user = User.objects.get(username=username)
                        print(f"DEBUG: Found user: {username}")
                    except User.DoesNotExist:
                        print(f"DEBUG: User not found: {username}")
                        pass
                
                # 정원 체크
                current_participants = meetup.current_participants
                print(f"DEBUG: Current participants: {current_participants}, Max: {meetup.max_participants}")
                if meetup.max_participants and current_participants >= meetup.max_participants:
                    print(f"DEBUG: Capacity exceeded")
                    error_messages.append(f'행 {row_num}: 밋업 정원이 초과되었습니다.')
                    break
                
                try:
                    print(f"DEBUG: Attempting to create order for {participant_name}")
                    # 참가자 추가 (수동 추가이므로 무료로 처리)
                    order = MeetupOrder.objects.create(
                        meetup=meetup,
                        user=user,
                        participant_name=participant_name,
                        participant_email=participant_email,
                        participant_phone=participant_phone,
                        base_price=0,  # 수동 추가는 무료
                        options_price=0,
                        total_price=0,
                        status='confirmed',
                        is_temporary_reserved=False,
                        confirmed_at=timezone.now(),
                        paid_at=timezone.now()  # 수동 추가는 즉시 확정
                    )
                    print(f"DEBUG: Order created successfully with ID: {order.id}")
                    
                    # 이메일 발송 시도 (실패해도 계속 진행)
                    try:
                        from ..services import send_meetup_participant_confirmation_email
                        send_meetup_participant_confirmation_email(order)
                        print(f"DEBUG: Email sent successfully")
                    except Exception as email_error:
                        print(f"DEBUG: Email sending failed: {email_error}")
                        pass
                    
                    success_count += 1
                    print(f"DEBUG: Added participant {participant_name} ({participant_email})")
                    
                    # 진행 상황을 더 잘 보기 위한 짧은 지연
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"DEBUG: Order creation failed: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    error_messages.append(f'행 {row_num}: 참가자 추가 실패 - {str(e)}')
            
            # 최종 진행 상황 업데이트
            update_progress(task_id, total_lines, total_lines, 'completed', f'처리 완료: 성공 {success_count}명, 오류 {len(error_messages)}건')
            
            # 결과 메시지
            print(f"DEBUG: Processing completed. Success: {success_count}, Errors: {len(error_messages)}")
            print(f"DEBUG: Error messages: {error_messages}")
            
            if success_count > 0:
                messages.success(request, f'{success_count}명의 참가자가 성공적으로 추가되었습니다.')
            
            if error_messages:
                for error_msg in error_messages[:10]:  # 최대 10개만 표시
                    messages.error(request, error_msg)
                if len(error_messages) > 10:
                    messages.warning(request, f'추가로 {len(error_messages) - 10}개의 오류가 있습니다.')
            
        except Exception as e:
            print(f"DEBUG: Exception occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            update_progress(task_id, 0, 1, 'error', f'오류 발생: {str(e)}')
            messages.error(request, f'CSV 파일 처리 중 오류가 발생했습니다: {str(e)}')
        
        # 처리 완료 - 리다이렉트하지 않고 진행 상황을 계속 보여줌
        print("DEBUG: Processing completed, showing progress result")
        
        # 진행 상황 페이지에서 결과를 보여주도록 context 전달
        context = {
            'meetup': meetup,
            'title': f'CSV로 참가자 추가 - {meetup.name}',
            'task_id': task_id,
            'processing_completed': True,
        }
        return render(request, 'admin/meetup/csv_upload_simple.html', context)
    
    # GET 요청: 폼 표시
    # 새로운 task_id 생성 (폼 제출용)
    task_id = str(uuid.uuid4())
    
    context = {
        'meetup': meetup,
        'title': f'CSV로 참가자 추가 - {meetup.name}',
        'task_id': task_id,
    }
    return render(request, 'admin/meetup/csv_upload_simple.html', context) 