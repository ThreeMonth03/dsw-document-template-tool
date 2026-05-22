# Translation Unit

- Source File: `src/projects.html.j2`
- Wrapper Name: `__tr_block_0010`
- Wrapper Order: `11`
- Wrapper Key: `grant-number-not-yet-given-planned-applied-granted-8d0eed8f00`
- Unit Key: `grant-number-not-yet-given-planned-applied-granted-6212e49d2a`
- Source Hash: `bad90d50edf8b99c7df5701a18cef34960f20522`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
{value}: {grantNumber} / grant number not yet given (planned) / (applied) / (granted) / (rejected)
```

### Source (en)

~~~jinja
<li>{{ macros.integrationCrossref(funderNameReply) }}: {{ grantNumber if grantNumber else "grant number not yet given" }} {% if funderStatus == uuids.funderStatusPlannedAUuid %}(planned){% elif funderStatus == uuids.funderStatusAppliedAUuid %}(applied){% elif funderStatus == uuids.funderStatusGrantedAUuid %}(granted){% elif funderStatus == uuids.funderStatusRejectedAUuid %}(rejected){% endif %}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
