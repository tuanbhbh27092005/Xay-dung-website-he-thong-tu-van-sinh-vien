from datetime import date, datetime, timedelta, time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q

from admin_panel.models import AdvisorProfile
from questions.models import Department
from notifications.models import Notification
from .models import AdvisorSchedule, Appointment
from .forms import AdvisorScheduleForm, AppointmentBookingForm, AppointmentUpdateStatusForm


def advisor_booking_list(request):
    """
    Trang danh sách cố vấn kèm lịch tiếp sinh viên để sinh viên lựa chọn đặt lịch.
    """
    dept_id = request.GET.get('department')
    search_q = request.GET.get('q', '').strip()

    advisors = AdvisorProfile.objects.filter(role='advisor').select_related('user', 'department')

    if dept_id:
        advisors = advisors.filter(department_id=dept_id)
    if search_q:
        advisors = advisors.filter(
            Q(user__first_name__icontains=search_q) |
            Q(user__last_name__icontains=search_q) |
            Q(position__icontains=search_q) |
            Q(department__name__icontains=search_q)
        )

    departments = Department.objects.all()

    context = {
        'advisors': advisors,
        'departments': departments,
        'selected_dept': int(dept_id) if dept_id and dept_id.isdigit() else None,
        'search_q': search_q,
    }
    return render(request, 'appointments/advisor_list.html', context)


@login_required
def book_advisor_slot(request, advisor_id):
    """
    Trang chọn ngày, xem khung giờ trống và đặt lịch hẹn 1-1 với Cố vấn học tập.
    """
    advisor = get_object_or_404(AdvisorProfile, id=advisor_id)

    # Lấy danh sách lịch định kỳ của cố vấn
    schedules = AdvisorSchedule.objects.filter(advisor=advisor, is_active=True)

    # Ngày được chọn (mặc định là ngày mai hoặc ngày trong request)
    selected_date_str = request.GET.get('date')
    today = timezone.localdate()
    min_date = today + timedelta(days=1)  # Đặt trước ít nhất 1 ngày
    max_date = today + timedelta(days=21)  # Trong vòng 3 tuần

    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            if selected_date < min_date or selected_date > max_date:
                selected_date = min_date
        except ValueError:
            selected_date = min_date
    else:
        selected_date = min_date

    # Lấy thứ trong tuần (0=Monday, 6=Sunday)
    day_of_week = selected_date.weekday()

    # Lấy khung giờ của cố vấn cho thứ này
    day_schedules = schedules.filter(day_of_week=day_of_week)

    # Chia nhỏ thành các slot (ca hẹn)
    slots = []
    # Lấy các cuộc hẹn đã được đặt vào ngày này
    booked_appointments = Appointment.objects.filter(
        advisor=advisor,
        date=selected_date,
        status__in=['pending', 'confirmed']
    )

    for sch in day_schedules:
        curr_time = datetime.combine(selected_date, sch.start_time)
        end_dt = datetime.combine(selected_date, sch.end_time)
        delta = timedelta(minutes=sch.slot_duration)

        while curr_time + delta <= end_dt:
            slot_start = curr_time.time()
            slot_end = (curr_time + delta).time()

            # Kiểm tra xem slot này đã bị trùng chưa
            is_booked = booked_appointments.filter(
                start_time__lt=slot_end,
                end_time__gt=slot_start
            ).exists()

            slots.append({
                'schedule_id': sch.id,
                'start_time': slot_start.strftime('%H:%M'),
                'end_time': slot_end.strftime('%H:%M'),
                'is_booked': is_booked,
                'default_note': sch.note,
            })
            curr_time += delta

    # Xử lý POST đặt lịch
    if request.method == 'POST':
        form = AppointmentBookingForm(request.POST)
        chosen_start_str = request.POST.get('start_time')
        chosen_end_str = request.POST.get('end_time')
        chosen_schedule_id = request.POST.get('schedule_id')

        if form.is_valid() and chosen_start_str and chosen_end_str:
            try:
                c_start = datetime.strptime(chosen_start_str, '%H:%M').time()
                c_end = datetime.strptime(chosen_end_str, '%H:%M').time()

                # Kiểm tra slot còn trống không
                conflict = Appointment.objects.filter(
                    advisor=advisor,
                    date=selected_date,
                    status__in=['pending', 'confirmed'],
                    start_time__lt=c_end,
                    end_time__gt=c_start,
                ).exists()

                if conflict:
                    messages.error(request, 'Khung giờ này vừa có người đặt hoặc đã bận. Vui lòng chọn ca khác!')
                else:
                    app = form.save(commit=False)
                    app.student = request.user
                    app.advisor = advisor
                    app.date = selected_date
                    app.start_time = c_start
                    app.end_time = c_end
                    if chosen_schedule_id:
                        app.schedule_id = chosen_schedule_id
                    app.status = 'pending'
                    app.save()

                    # Gửi thông báo cho Cố vấn học tập
                    try:
                        Notification.notify(
                            recipient=advisor.user,
                            actor=request.user,
                            verb=f"Sinh viên {request.user.get_full_name() or request.user.username} đã đặt lịch tư vấn 1-1 ({selected_date.strftime('%d/%m/%Y')} {chosen_start_str}-{chosen_end_str})",
                            target_url=reverse('appointments:manage_appointments')
                        )
                    except Exception:
                        pass

                    messages.success(request, f'Đăng ký lịch tư vấn 1-1 với {advisor.display_name} thành công! Vui lòng chờ thầy/cô xác nhận.')
                    return redirect('appointments:student_appointments')
            except Exception as e:
                messages.error(request, f'Lỗi khi đặt lịch: {e}')
        else:
            messages.error(request, 'Vui lòng điền đầy đủ thông tin và chọn một khung giờ hợp lệ.')
    else:
        form = AppointmentBookingForm()

    context = {
        'advisor': advisor,
        'schedules': schedules,
        'selected_date': selected_date,
        'min_date': min_date.strftime('%Y-%m-%d'),
        'max_date': max_date.strftime('%Y-%m-%d'),
        'slots': slots,
        'form': form,
    }
    return render(request, 'appointments/book_slot.html', context)


@login_required
def student_appointment_list(request):
    """
    Trang xem danh sách các lịch hẹn của sinh viên hiện tại.
    """
    appointments = Appointment.objects.filter(student=request.user).select_related('advisor', 'advisor__user', 'advisor__department')
    return render(request, 'appointments/student_appointments.html', {'appointments': appointments})


@login_required
def cancel_appointment(request, appointment_id):
    """
    Hủy lịch hẹn (dành cho sinh viên hoặc cố vấn).
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Chỉ student hoặc advisor liên quan mới được hủy
    is_owner = (appointment.student_id == request.user.id)
    is_advisor = hasattr(request.user, 'advisorprofile') and (appointment.advisor_id == request.user.advisorprofile.id)

    if not (is_owner or is_advisor or request.user.is_superuser):
        return HttpResponseForbidden("Bạn không có quyền hủy cuộc hẹn này.")

    if request.method == 'POST':
        reason = request.POST.get('cancel_reason', '').strip()
        appointment.status = 'canceled'
        appointment.cancel_reason = reason or ('Hủy bởi sinh viên' if is_owner else 'Hủy bởi Cố vấn')
        appointment.save()

        # Bắn thông báo cho đối phương
        target_user = appointment.advisor.user if is_owner else appointment.student
        notify_text = f"Cuộc hẹn ngày {appointment.date.strftime('%d/%m/%Y')} lúc {appointment.start_time.strftime('%H:%M')} đã bị hủy."
        if reason:
            notify_text += f" Lý do: {reason}"

        Notification.notify(
            recipient=target_user,
            actor=request.user,
            verb=notify_text,
            target_url=reverse('appointments:manage_appointments') if is_owner else reverse('appointments:student_appointments')
        )

        messages.success(request, 'Đã hủy lịch hẹn thành công.')
        if is_owner:
            return redirect('appointments:student_appointments')
        return redirect('appointments:manage_appointments')

    return render(request, 'appointments/confirm_cancel.html', {'appointment': appointment})


# ==============================================================
# PHÂN HỆ QUẢN LÝ DÀNH CHO CỐ VẤN / BAN TƯ VẤN (ADVISOR PANEL)
# ==============================================================

@login_required
def advisor_manage_appointments(request):
    """
    Trang Cố vấn xem danh sách các cuộc hẹn của sinh viên đăng ký với mình.
    """
    if not hasattr(request.user, 'advisorprofile'):
        return HttpResponseForbidden("Bạn không có quyền truy cập trang này.")

    advisor = request.user.advisorprofile
    status_filter = request.GET.get('status', '')

    appointments = Appointment.objects.filter(advisor=advisor).select_related('student')
    if status_filter:
        appointments = appointments.filter(status=status_filter)

    pending_count = Appointment.objects.filter(advisor=advisor, status='pending').count()
    confirmed_count = Appointment.objects.filter(advisor=advisor, status='confirmed').count()
    completed_count = Appointment.objects.filter(advisor=advisor, status='completed').count()

    context = {
        'appointments': appointments,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'completed_count': completed_count,
    }
    return render(request, 'appointments/manage_appointments.html', context)


@login_required
def advisor_update_appointment(request, appointment_id):
    """
    Cố vấn duyệt / từ chối / hoàn thành và cập nhật link phòng trực tuyến/phòng gặp.
    """
    if not hasattr(request.user, 'advisorprofile'):
        return HttpResponseForbidden("Bạn không có quyền truy cập.")

    advisor = request.user.advisorprofile
    appointment = get_object_or_404(Appointment, id=appointment_id, advisor=advisor)

    if request.method == 'POST':
        form = AppointmentUpdateStatusForm(request.POST, instance=appointment)
        if form.is_valid():
            updated_app = form.save()

            # Thông báo cho sinh viên
            status_text = {
                'confirmed': 'đã được Cố vấn XÁC NHẬN. Vui lòng kiểm tra địa điểm / link Meet!',
                'completed': 'đã HOÀN THÀNH. Cảm ơn bạn!',
                'canceled': f"đã BỊ TỪ CHỐI/HỦY. Lý do: {updated_app.cancel_reason or 'Không có'}",
            }.get(updated_app.status, 'đã được cập nhật trạng thái.')

            Notification.notify(
                recipient=updated_app.student,
                actor=request.user,
                verb=f"Lịch tư vấn ngày {updated_app.date.strftime('%d/%m/%Y')} {status_text}",
                target_url=reverse('appointments:student_appointments')
            )

            messages.success(request, f'Cập nhật trạng thái lịch hẹn của sinh viên {updated_app.student.get_full_name() or updated_app.student.username} thành công!')
            return redirect('appointments:manage_appointments')
    else:
        form = AppointmentUpdateStatusForm(instance=appointment)

    return render(request, 'appointments/update_appointment.html', {'form': form, 'appointment': appointment})


@login_required
def advisor_schedule_settings(request):
    """
    Cố vấn cấu hình lịch tiếp sinh viên định kỳ (thứ mấy, từ mấy giờ đến mấy giờ).
    """
    if not hasattr(request.user, 'advisorprofile'):
        return HttpResponseForbidden("Bạn không có quyền truy cập.")

    advisor = request.user.advisorprofile
    schedules = AdvisorSchedule.objects.filter(advisor=advisor)

    if request.method == 'POST':
        form = AdvisorScheduleForm(request.POST)
        if form.is_valid():
            sch = form.save(commit=False)
            sch.advisor = advisor
            sch.save()
            messages.success(request, 'Đã thêm khung giờ tiếp sinh viên thành công!')
            return redirect('appointments:schedule_settings')
    else:
        form = AdvisorScheduleForm()

    return render(request, 'appointments/schedule_settings.html', {'form': form, 'schedules': schedules})


@login_required
def delete_advisor_schedule(request, schedule_id):
    """
    Xóa khung giờ tiếp sinh viên.
    """
    if not hasattr(request.user, 'advisorprofile'):
        return HttpResponseForbidden("Bạn không có quyền truy cập.")

    advisor = request.user.advisorprofile
    sch = get_object_or_404(AdvisorSchedule, id=schedule_id, advisor=advisor)
    sch.delete()
    messages.success(request, 'Đã xóa khung giờ tiếp sinh viên.')
    return redirect('appointments:schedule_settings')
