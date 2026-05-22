# Translation Unit

- Source File: `src/contributors.html.j2`
- Wrapper Name: `__tr_block_0002`
- Wrapper Order: `3`
- Wrapper Key: `role-roles-affiliation-9e2e664901`
- Unit Key: `role-roles-206ea60d1d`
- Source Hash: `891d0f51096ff4d98301200da961c54e18bde846`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
Role / Roles:
```

### Source (en)

~~~jinja
{% if contributor.roles|length == 0 %}Role{% else %}Roles{% endif %}: {% for role in contributor.roles %}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
