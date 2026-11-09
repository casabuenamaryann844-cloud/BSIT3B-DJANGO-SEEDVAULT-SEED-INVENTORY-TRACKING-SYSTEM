import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import SeedInventory, LOW_STOCK_THRESHOLD
from .forms import SeedInventoryForm


User = get_user_model()

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=1)
INVALID_LOGIN_MESSAGE = 'Invalid username or password.'
LOCKED_MESSAGE = 'Too many failed attempts. Locked for 1 minute.'

INVENTORY_PAGE_SIZE = 25
EXPIRY_WINDOW_DAYS = 30
STATUS_FILTERS = {
    "available": {"quantity__gt": LOW_STOCK_THRESHOLD},
    "low": {"quantity__gt": 0, "quantity__lte": LOW_STOCK_THRESHOLD},
    "out": {"quantity": 0},
}


def _query_string(params):
    query = QueryDict("", mutable=True)
    for key, value in params.items():
        query[key] = value
    return query.urlencode()


def _quantity_by_unit(seeds):
    labels = dict(SeedInventory.UNIT_CHOICES)
    rows = [
        {
            "unit": labels.get(row["unit"], row["unit"]),
            "total": row["total"] or 0,
        }
        for row in seeds.values("unit").annotate(total=Sum("quantity"))
    ]
    rows.sort(key=lambda row: row["total"], reverse=True)
    return rows


def _filter_seeds(request, seeds=None):
    """Shared q / category / location / status filtering for the list and export."""
    if seeds is None:
        seeds = SeedInventory.objects.all()

    params = {}

    q = request.GET.get("q", "").strip()
    if q:
        seeds = seeds.filter(
            Q(seed_name__icontains=q)
            | Q(variety__icontains=q)
            | Q(storage_location__icontains=q)
            | Q(notes__icontains=q)
        )
        params["q"] = q

    category = request.GET.get("category", "").strip()
    if category in dict(SeedInventory.CATEGORY_CHOICES):
        seeds = seeds.filter(category=category)
        params["category"] = category

    location = request.GET.get("location", "").strip()
    if location:
        seeds = seeds.filter(storage_location__iexact=location)
        params["location"] = location

    status = request.GET.get("status", "").strip()
    if status in STATUS_FILTERS:
        seeds = seeds.filter(**STATUS_FILTERS[status])
        params["status"] = status

    return seeds.order_by("seed_name"), params


# LOGIN LOCK FUNCTIONS

def _reset_lock_state(request):
    request.session['failed_attempts'] = 0
    request.session['lock_time'] = None


def _get_lock_state(request):
    failed_attempts = request.session.get('failed_attempts', 0)
    lock_time = request.session.get('lock_time')

    if not lock_time:
        return failed_attempts, None

    try:
        unlock_time = timezone.datetime.fromisoformat(lock_time)
    except (TypeError, ValueError):
        _reset_lock_state(request)
        return 0, None

    if timezone.now() < unlock_time:
        remaining = int(
            (unlock_time - timezone.now()).total_seconds()
        )
        return failed_attempts, remaining

    _reset_lock_state(request)
    return 0, None


def _set_lock_state(request):
    lock_until = timezone.now() + LOCK_DURATION
    request.session['failed_attempts'] = MAX_FAILED_ATTEMPTS
    request.session['lock_time'] = lock_until.isoformat()
    return int(LOCK_DURATION.total_seconds())


# REGISTRATION VALIDATION

def _validate_registration_data(data):
    errors = {}

    username = data.get('username', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not username:
        errors['username'] = 'Username is required.'
    elif User.objects.filter(username=username).exists():
        errors['username'] = 'Username already taken.'

    if not first_name:
        errors['first_name'] = 'First name is required.'

    if not last_name:
        errors['last_name'] = 'Last name is required.'

    if not email:
        errors['email'] = 'Email is required.'
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = 'Enter a valid email address.'
        else:
            if User.objects.filter(email=email).exists():
                errors['email'] = 'Email already registered.'

    if not password:
        errors['password'] = 'Password is required.'
    elif len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters.'
    else:
        try:
            validate_password(password)
        except ValidationError as exc:
            errors['password'] = ' '.join(exc.messages)

    if password != confirm_password:
        errors['confirm_password'] = 'Passwords do not match.'

    return errors


# LOGIN

@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    failed_attempts, remaining = _get_lock_state(request)

    if remaining is not None:
        messages.error(
            request,
            f'Too many failed attempts. Try again in {remaining} seconds.'
        )
        return render(
            request,
            'auth/login.html',
            {'locked': True, 'remaining': remaining}
        )

    if request.method == 'GET':
        return render(request, 'auth/login.html')

    identifier = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    remember_me = request.POST.get('remember_me') == 'on'

    username = identifier
    if '@' in identifier:
        match = User.objects.filter(email__iexact=identifier).first()
        if match is not None:
            username = match.username

    user = authenticate(
        request,
        username=username,
        password=password
    )

    if user is not None:
        _reset_lock_state(request)
        login(request, user)
        request.session.set_expiry(14 * 24 * 60 * 60 if remember_me else 0)
        return redirect('dashboard')

    failed_attempts += 1
    request.session['failed_attempts'] = failed_attempts

    if failed_attempts >= MAX_FAILED_ATTEMPTS:
        remaining = _set_lock_state(request)
        messages.error(request, LOCKED_MESSAGE)
        return render(
            request,
            'auth/login.html',
            {'locked': True, 'remaining': remaining}
        )

    remaining_attempts = MAX_FAILED_ATTEMPTS - failed_attempts
    messages.error(
        request,
        f'{INVALID_LOGIN_MESSAGE} {remaining_attempts} attempts remaining.'
    )
    return render(request, 'auth/login.html')


# LOGOUT

def logout_view(request):
    logout(request)
    return redirect('login')


# DASHBOARD


@login_required
def home(request):
    today = timezone.localdate()
    window_end = today + timedelta(days=EXPIRY_WINDOW_DAYS)
    seeds = SeedInventory.objects.all()

    total_records = seeds.count()
    out_of_stock = seeds.filter(**STATUS_FILTERS["out"]).count()
    low_stock = seeds.filter(**STATUS_FILTERS["low"]).count()
    available = seeds.filter(**STATUS_FILTERS["available"]).count()

    expiring_soon = seeds.filter(
        expiration_date__gte=today,
        expiration_date__lte=window_end,
    ).count()

    expired = seeds.filter(
        expiration_date__lt=today
    ).count()

    attention = []
    for seed in seeds.filter(
        Q(**STATUS_FILTERS["out"])
        | Q(**STATUS_FILTERS["low"])
        | Q(expiration_date__lt=today)
        | Q(expiration_date__gte=today, expiration_date__lte=window_end)
    ).order_by("seed_name"):
        if seed.quantity == 0:
            reason, tone = "Out of stock", "danger"
        elif seed.expiration_date and seed.expiration_date < today:
            reason, tone = "Expired", "danger"
        elif seed.quantity <= LOW_STOCK_THRESHOLD:
            reason, tone = "Low stock", "warning"
        else:
            reason, tone = "Expiring soon", "warning"
        attention.append({"seed": seed, "reason": reason, "tone": tone})

    context = {
        "total_records": total_records,
        "available": available,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "expiring_soon": expiring_soon,
        "expired": expired,
        "quantity_by_unit": _quantity_by_unit(seeds),
        "attention": attention[:8],
        "attention_count": len(attention),
        "recent_seeds": seeds.order_by("-date_added")[:5],
    }

    return render(request, "home.html", context)


# REGISTRATION

@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'GET':
        return render(request, 'auth/register.html')

    form_data = {
        'username': request.POST.get('username', ''),
        'first_name': request.POST.get('first_name', ''),
        'last_name': request.POST.get('last_name', ''),
        'email': request.POST.get('email', ''),
        'password': request.POST.get('password', ''),
        'confirm_password': request.POST.get('confirm_password', ''),
    }

    errors = _validate_registration_data(form_data)

    if errors:
        return render(
            request,
            'auth/register.html',
            {'errors': errors, 'form_data': form_data}
        )

    user = User.objects.create_user(
        username=form_data['username'].strip(),
        first_name=form_data['first_name'].strip(),
        last_name=form_data['last_name'].strip(),
        email=form_data['email'].strip(),
        password=form_data['password'],
    )

    login(request, user)
    return redirect('dashboard')


# SEED INVENTORY LIST

@login_required(login_url='login')
def inventory_list(request):
    seeds, params = _filter_seeds(request)

    paginator = Paginator(seeds, INVENTORY_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        'inventory/list.html',
        {
            'seeds': page.object_list,
            'page_obj': page,
            'paginator': paginator,
            'is_filtered': bool(params),
            'result_count': paginator.count,
            'query_string': _query_string(params),
            'category_choices': SeedInventory.CATEGORY_CHOICES,
            'location_choices': (
                SeedInventory.objects
                .exclude(storage_location='')
                .values_list('storage_location', flat=True)
                .distinct()
                .order_by('storage_location')
            ),
            'active': params,
        }
    )


@login_required(login_url='login')
def inventory_export(request):
    seeds, _ = _filter_seeds(request)

    category_labels = dict(SeedInventory.CATEGORY_CHOICES)
    unit_labels = dict(SeedInventory.UNIT_CHOICES)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="seed_inventory_{timezone.localdate():%Y%m%d}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'Seed Name', 'Variety', 'Category', 'Quantity', 'Unit',
        'Storage Location', 'Expiration Date', 'Status', 'Notes',
    ])
    for seed in seeds:
        writer.writerow([
            seed.seed_name,
            seed.variety,
            category_labels.get(seed.category, seed.category),
            seed.quantity,
            unit_labels.get(seed.unit, seed.unit),
            seed.storage_location,
            seed.expiration_date.isoformat() if seed.expiration_date else '',
            seed.stock_status,
            seed.notes,
        ])

    return response


# ADD SEED


@login_required
@require_http_methods(["GET", "POST"])
def inventory_create(request):
    if request.method == "POST":
        form = SeedInventoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Seed added successfully!")
            return redirect("inventory_list")
    else:
        form = SeedInventoryForm()

    return render(request, "inventory/form.html", {
        "form": form,
        "title": "Add Seed",
        "submit_label": "Save Seed",
    })


# EDIT SEED

@login_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def inventory_edit(request, pk):
    seed = get_object_or_404(SeedInventory, pk=pk)
    form = SeedInventoryForm(request.POST or None, request.FILES or None, instance=seed)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Seed record updated successfully.')
        return redirect('inventory_list')

    return render(
        request,
        'inventory/form.html',
        {
            'form': form,
            'title': 'Edit Seed',
            'submit_label': 'Update Seed',
        }
    )


# DELETE SEED

@login_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def inventory_delete(request, pk):
    seed = get_object_or_404(SeedInventory, pk=pk)

    if request.method == 'POST':
        seed.delete()
        messages.success(request, 'Seed record deleted successfully.')
        return redirect('inventory_list')

    return render(
        request,
        'inventory/confirm_delete.html',
        {'seed': seed}
    )


@login_required
def seed_categories(request):
    categories = []

    for value, label in SeedInventory.CATEGORY_CHOICES:
        categories.append({
            "name": label,
            "count": SeedInventory.objects.filter(
                category=value
            ).count(),
        })

    return render(request, "inventory/section.html", {
        "title": "Seed Categories",
        "description": "Browse seed records by category.",
        "kind": "categories",
        "categories": categories,
    })


@login_required
def storage_locations(request):
    rows = (
        SeedInventory.objects
        .exclude(storage_location="")
        .values("storage_location")
        .annotate(count=Count("id"))
    )

    merged = {}
    for row in rows:
        name = row["storage_location"].strip()
        if not name:
            continue
        key = name.lower()
        entry = merged.setdefault(key, {"name": name, "count": 0})
        entry["count"] += row["count"]

    locations = sorted(merged.values(), key=lambda item: item["name"].lower())

    return render(request, "inventory/section.html", {
        "title": "Storage Locations",
        "description": "View locations where seeds are stored.",
        "kind": "locations",
        "locations": locations,
    })


@login_required
def seed_status(request):
    seeds = SeedInventory.objects.all().order_by("seed_name")

    rows = [{"seed": seed, "status": seed.stock_status} for seed in seeds]

    return render(request, "inventory/section.html", {
        "title": "Seed Status",
        "description": (
            f"Monitor available, low-stock (at or below "
            f"{LOW_STOCK_THRESHOLD} units) and out-of-stock seeds."
        ),
        "kind": "status",
        "rows": rows,
    })


@login_required
def inventory_reports(request):
    seeds = SeedInventory.objects.all()

    return render(request, "inventory/section.html", {
        "title": "Reports",
        "description": "Summary of your current seed inventory.",
        "kind": "reports",
        "total_records": seeds.count(),
        "available": seeds.filter(**STATUS_FILTERS["available"]).count(),
        "low_stock": seeds.filter(**STATUS_FILTERS["low"]).count(),
        "out_of_stock": seeds.filter(**STATUS_FILTERS["out"]).count(),
        "quantity_by_unit": _quantity_by_unit(seeds),
    })


# EXPIRY TRACKING


@login_required
def seed_expiry(request):
    today = timezone.localdate()
    window_end = today + timedelta(days=EXPIRY_WINDOW_DAYS)

    dated = SeedInventory.objects.exclude(
        expiration_date__isnull=True
    ).order_by("expiration_date")

    expired = dated.filter(expiration_date__lt=today)
    expiring_soon = dated.filter(
        expiration_date__gte=today,
        expiration_date__lte=window_end,
    )
    missing_date = SeedInventory.objects.filter(
        expiration_date__isnull=True
    ).count()

    active_view = request.GET.get("view", "all")
    if active_view not in {"all", "expired", "soon"}:
        active_view = "all"

    titles = {
        "expired": "Expired Seeds",
        "soon": f"Expiring Within {EXPIRY_WINDOW_DAYS} Days",
    }

    return render(request, "inventory/section.html", {
        "title": titles.get(active_view, "Expiry Tracking"),
        "description": (
            f"Seeds expiring within {EXPIRY_WINDOW_DAYS} days "
            "and those already expired."
        ),
        "kind": "expiry",
        "active_view": active_view,
        "expired": expired,
        "expiring_soon": expiring_soon,
        "at_risk_count": expired.count() + expiring_soon.count(),
        "missing_date": missing_date,
        "today": today,
    })
