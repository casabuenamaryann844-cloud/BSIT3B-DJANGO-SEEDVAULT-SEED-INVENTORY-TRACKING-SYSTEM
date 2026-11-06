from django.shortcuts import render
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Q

from apps.scoping import scoped_info, scoped_infos
from apps.core.models import SeedInventory
from .models import Info

MIN_AGE = 1
MAX_AGE = 150


def _parse_int(raw_value):
    """Convert a submitted number to an integer, returning None when it is invalid."""
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _seed_payload(info):
    """Shape the seed link of a distribution record for JSON and template use."""
    return {
        'seed': info.seed_id,
        'seed_name': info.seed.seed_name if info.seed else '',
        'seed_unit': info.seed.unit if info.seed else '',
        'quantity_issued': info.quantity_issued,
    }


@login_required(login_url='login')
def info_list_page(request):
    """Render the searchable, paginated distribution list for the signed-in user."""
    query = request.GET.get('q', '').strip()

    infos_list = scoped_infos(request.user).select_related('seed').order_by('name')

    if query:
        infos_list = infos_list.filter(
            Q(name__icontains=query) |
            Q(address__icontains=query) |
            Q(email__icontains=query)
        )

    paginator = Paginator(infos_list, 10)
    page_number = request.GET.get('page', 1)
    infos = paginator.get_page(page_number)

    return render(request, 'info.html', {
        'infos': infos,
        'query': query,
        'seeds': SeedInventory.objects.all(),
    })


@login_required(login_url='login')
def info_list_ajax(request):
    """Return the signed-in user's filtered distribution records as paginated JSON."""
    query = request.GET.get('q', '').strip()

    infos_list = scoped_infos(request.user).select_related('seed').order_by('name')

    if query:
        infos_list = infos_list.filter(
            Q(name__icontains=query) |
            Q(address__icontains=query) |
            Q(email__icontains=query)
        )

    paginator = Paginator(infos_list, 10)
    page_number = request.GET.get('page', 1)
    infos = paginator.get_page(page_number)
    data = [
        {
            'id': info.id,
            'name': info.name,
            'age': info.age,
            'address': info.address,
            'email': info.email,
            'seed': info.seed_id,
            'seed_name': info.seed.seed_name if info.seed else '',
            'quantity_issued': info.quantity_issued,
        }
        for info in infos.object_list
    ]
    return JsonResponse({
        'data': data,
        'has_next': infos.has_next(),
        'has_prev': infos.has_previous(),
        'page': infos.number,
        'pages': infos.paginator.num_pages,
        'total': infos.paginator.count,
    })


@login_required(login_url='login')
def info_get_ajax(request, pk):
    """Return one of the signed-in user's distribution records as JSON."""
    info = scoped_info(request.user, pk)
    return JsonResponse({
        'id': info.id,
        'name': info.name,
        'age': info.age,
        'address': info.address,
        'email': info.email,
        **_seed_payload(info),
    })


@login_required(login_url='login')
@require_POST
def info_save_ajax(request):
    """Validate and create or update a distribution record, returning its data as JSON."""
    info_id = request.POST.get('id')

    if info_id:
        info = scoped_info(request.user, info_id)
        is_update = True
    else:
        info = Info()
        is_update = False

    name = request.POST.get('name', '').strip()
    age = request.POST.get('age', '').strip()
    address = request.POST.get('address', '').strip()
    email = request.POST.get('email', '').strip()
    seed_id = request.POST.get('seed', '').strip()
    quantity_issued = request.POST.get('quantity_issued', '').strip()

    if not name:
        return JsonResponse({'error': 'Name is required.'}, status=400)

    if not age:
        return JsonResponse({'error': 'Age is required.'}, status=400)

    age_value = _parse_int(age)

    if age_value is None or age_value < MIN_AGE or age_value > MAX_AGE:
        return JsonResponse(
            {'error': f'Age must be a number between {MIN_AGE} and {MAX_AGE}.'},
            status=400
        )

    if not address:
        return JsonResponse({'error': 'Address is required.'}, status=400)

    if email:
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'error': 'Enter a valid email address.'}, status=400)

    seed = None

    if seed_id:
        seed = SeedInventory.objects.filter(pk=seed_id).first()

        if seed is None:
            return JsonResponse({'error': 'Select a seed from the inventory.'}, status=400)

    if quantity_issued:
        quantity_value = _parse_int(quantity_issued)

        if quantity_value is None or quantity_value < 0:
            return JsonResponse(
                {'error': 'Quantity issued must be a whole number of 0 or more.'},
                status=400
            )
    else:
        quantity_value = 0

    if seed is not None and quantity_value == 0:
        return JsonResponse(
            {'error': 'Enter how many seeds were issued to this recipient.'},
            status=400
        )

    info.name = name
    info.age = age_value
    info.address = address
    info.email = email
    info.seed = seed
    info.quantity_issued = quantity_value

    if not info.pk:
        info.user = request.user

    try:
        info.save()
    except IntegrityError:
        return JsonResponse(
            {'error': 'Could not save record due to a conflict.'},
            status=400
        )

    saved = 'updated' if is_update else 'saved'

    if seed is not None:
        messages.success(
            request,
            f'Distribution for "{info.name}" '
            f'({info.quantity_issued} {seed.unit} of {seed.seed_name}) has been {saved} successfully.'
        )
    else:
        messages.success(request, f'Record "{info.name}" has been {saved} successfully.')

    return JsonResponse({
        'status': 'success',
        'id': info.id,
        'name': info.name,
        'age': info.age,
        'address': info.address,
        'email': info.email,
        **_seed_payload(info),
    })


@login_required(login_url='login')
@require_POST
def info_delete_ajax(request, pk):
    """Delete the specified signed-in user's distribution record and confirm as JSON."""
    info = scoped_info(request.user, pk)
    info_name = info.name
    info.delete()
    messages.success(request, f'Record "{info_name}" has been deleted successfully.')
    return JsonResponse({'status': 'deleted'})
