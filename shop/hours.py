from datetime import date, datetime, time, timedelta

from django.utils import timezone

from .models import ExceptionalClosure, OpeningPeriod


def periods_for_date(day):
    exception = ExceptionalClosure.objects.filter(date=day).first()
    if exception:
        if exception.is_closed:
            return []
        return [(exception.opens_at, exception.closes_at)]
    return list(
        OpeningPeriod.objects.filter(weekday=day.weekday(), is_active=True)
        .values_list('opens_at', 'closes_at')
    )


def is_valid_service_time(day, at_time):
    return any(start <= at_time < end for start, end in periods_for_date(day))


def collection_slots(day, interval_minutes=15, lead_minutes=30):
    now = timezone.localtime()
    if day < now.date():
        return []
    slots = []
    for start, end in periods_for_date(day):
        cursor = timezone.make_aware(datetime.combine(day, start))
        closing = timezone.make_aware(datetime.combine(day, end))
        earliest = now + timedelta(minutes=lead_minutes)
        if day == now.date() and cursor < earliest:
            rounded_minutes = ((earliest.minute // interval_minutes) + 1) * interval_minutes
            cursor = earliest.replace(second=0, microsecond=0)
            if rounded_minutes >= 60:
                cursor = cursor.replace(minute=0) + timedelta(hours=1)
            else:
                cursor = cursor.replace(minute=rounded_minutes)
        while cursor + timedelta(minutes=interval_minutes) <= closing:
            slots.append(cursor.time().replace(second=0, microsecond=0))
            cursor += timedelta(minutes=interval_minutes)
    return slots


def next_opening(after=None, days=14):
    current = timezone.localtime(after) if after else timezone.localtime()
    for offset in range(days + 1):
        day = current.date() + timedelta(days=offset)
        for start, end in periods_for_date(day):
            opening = timezone.make_aware(datetime.combine(day, start))
            closing = timezone.make_aware(datetime.combine(day, end))
            if opening <= current < closing:
                return {'is_open': True, 'day': day, 'time': start, 'closes_at': end}
            if opening > current:
                return {'is_open': False, 'day': day, 'time': start, 'closes_at': end}
    return None


def restaurant_status(now=None):
    current = timezone.localtime(now) if now else timezone.localtime()
    opening = next_opening(current)
    if not opening:
        return {
            'is_open': False,
            'label': 'Fermé',
            'detail': 'Horaires temporairement indisponibles',
        }
    if opening['is_open']:
        return {
            'is_open': True,
            'label': 'Ouvert maintenant',
            'detail': f"Ferme à {opening['closes_at']:%H:%M}",
        }
    if opening['day'] == current.date():
        detail = f"Ouvre aujourd’hui à {opening['time']:%H:%M}"
    elif opening['day'] == current.date() + timedelta(days=1):
        detail = f"Ouvre demain à {opening['time']:%H:%M}"
    else:
        weekday = OpeningPeriod.WEEKDAYS[opening['day'].weekday()][1].lower()
        detail = f"Ouvre {weekday} à {opening['time']:%H:%M}"
    return {'is_open': False, 'label': 'Fermé', 'detail': detail}


def weekly_hours():
    rows = []
    labels = dict(OpeningPeriod.WEEKDAYS)
    for weekday in range(7):
        periods = list(
            OpeningPeriod.objects.filter(weekday=weekday, is_active=True)
            .values_list('opens_at', 'closes_at')
        )
        rows.append({
            'weekday': weekday,
            'label': labels[weekday],
            'periods': periods,
            'display': ' / '.join(f'{start:%H:%M}–{end:%H:%M}' for start, end in periods) or 'Fermé',
        })
    return rows
