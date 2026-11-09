# Role-Based Account Creation

The Register page (`/register/`) creates one account per selected role. All three
roles use Django's built-in `User` model, so no database migration is required.

## Roles

| Role | Stored as | Access in SeedVault |
| --- | --- | --- |
| Administrator | `is_superuser=True`, `is_staff=True` | All pages, plus **Manage Users** (create, edit, deactivate, delete accounts) |
| Staff | `is_staff=True` | Dashboard and inventory pages (same in-app pages as Instructor; the staff flag identifies staff-level accounts, e.g. Django admin) |
| Instructor | regular account | Dashboard and inventory pages |
3
The role label shown in the sidebar follows the same mapping: Administrator,
Staff, Instructor.

## Register flow

1. Open `/register/`.
2. Fill in first name, last name, username, and email.
3. Pick a role: **Instructor**, **Staff**, or **Administrator**.
4. If **Administrator** is picked, the **Administrator Access Code** field appears
   and is required.
5. Enter the password twice, then submit.

On success the account is created with a hashed password, the new user is logged
in immediately, and is redirected to `/home/`.

Default role is Instructor (least privilege). The role radios, the conditional
access-code field, password toggles, and the login link are all wired in
`static/js/auth.js`.

## Administrator access code

Public registration must not create an administrator silently. The code is
checked server-side with `secrets.compare_digest` in
`apps/core/views.py` (`_validate_registration_data`), so it cannot be bypassed
by disabling JavaScript.

- Setting: `ADMIN_REGISTRATION_CODE` in `mysite/settings.py`
- Environment override: `SEEDVAULT_ADMIN_CODE`
- Default value: `SEEDVAULT-ADMIN-2026`

The default works out of the box. Before deploying, set your own value:

```bash
export SEEDVAULT_ADMIN_CODE="your-own-code"
```

(PowerShell: `$env:SEEDVAULT_ADMIN_CODE = "your-own-code"`)

The code is never echoed back into the form after a failed submit.

## Validation rules

| Field | Rule |
| --- | --- |
| First name, last name | Required |
| Username | Required, unique |
| Email | Required, valid format, unique |
| Role | Must be `instructor`, `staff`, or `administrator` |
| Administrator access code | Required for Administrator, compared in constant time |
| Password | At least 8 characters, passes Django password validators |
| Confirm password | Must match |

Errors are rendered next to the field and the form keeps the other entries.

## Other ways to create accounts

- Administrator via terminal: `py manage.py createsuperuser`
- Administrator via web: **Manage Users** (`/users/`), superuser-only. This page
  can also create Staff or Instructor accounts and activate/deactivate them.

## Notes

- `is_staff` and `is_superuser` are the only persisted role flags; the role
  picker maps directly to them.
- Only Administrator accounts can open Manage Users; Staff and Instructor
  accounts are redirected to the dashboard from that page.
- Existing accounts are unaffected. Accounts created before this change have
  `is_staff=False` and `is_superuser=False`, so they appear as Instructor.
