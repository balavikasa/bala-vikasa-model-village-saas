# CSRF login compatibility fix

Version `2026.27.2` changes `WTF_CSRF_TIME_LIMIT` from a
`datetime.timedelta` to integer seconds (`43200` by default).

Flask-WTF forwards this value to `itsdangerous.URLSafeTimedSerializer.loads`
as `max_age`. ItsDangerous compares an integer token age with `max_age`, so a
`timedelta` causes:

```text
TypeError: '>' not supported between instances of 'int' and 'datetime.timedelta'
```

The lifetime can be configured through:

```dotenv
WTF_CSRF_TIME_LIMIT_SECONDS=43200
```

After updating a running local checkout, stop Flask, delete browser cookies
for `127.0.0.1`, restart Flask, reload `/login`, and submit the newly generated
token.
