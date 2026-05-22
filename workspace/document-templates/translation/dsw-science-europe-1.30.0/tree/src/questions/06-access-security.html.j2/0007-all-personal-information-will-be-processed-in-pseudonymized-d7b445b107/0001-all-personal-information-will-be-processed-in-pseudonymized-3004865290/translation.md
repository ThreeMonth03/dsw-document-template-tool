# Translation Unit

- Source File: `src/questions/06-access-security.html.j2`
- Wrapper Name: `__tr_block_0006`
- Wrapper Order: `7`
- Wrapper Key: `all-personal-information-will-be-processed-in-pseudonymized-d7b445b107`
- Unit Key: `all-personal-information-will-be-processed-in-pseudonymized-3004865290`
- Source Hash: `c95029fc15ee4547df32e15481762eabf4036f04`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
All personal information will be processed in pseudonymized form only. We pseudonymize inside the project, only limited people can access the keys. / Pseudonymization is handled by an independent party in order to allow data coupling. / We have a specific way of pseudonymization{value}
```

### Source (en)

~~~jinja
All personal information will be processed in pseudonymized form only.
        {%- set risksPseudonymizationPath = [risksPersonalDataPath, uuids.risksPersonalDataPseudoAUuid, uuids.risksPseudonymizationQUuid]|reply_path -%}
        {%- set risksPseudonymizationAUuid = repliesMap[risksPseudonymizationPath]|reply_str_value -%}
        {%- if risksPseudonymizationAUuid == uuids.risksPseudonymizationInsideAUuid %}
          We pseudonymize inside the project, only limited people can access the keys.
        {%- elif risksPseudonymizationAUuid == uuids.risksPseudonymizationPartyAUuid %}
          Pseudonymization is handled by an independent party in order to allow data coupling.
        {%- elif risksPseudonymizationAUuid == uuids.risksPseudonymizationAnotherAUuid -%}
          {%- set risksPseudonymizationAnotherQUuid = [risksPseudonymizationPath, uuids.risksPseudonymizationAnotherAUuid, uuids.risksPseudonymizationAnotherQUuid]|reply_path -%}
          {%- set risksPseudonymizationAnother = repliesMap[risksPseudonymizationAnotherQUuid]|reply_str_value %}
          We have a specific way of pseudonymization{{ ": " ~ risksPseudonymizationAnother|dot if risksPseudonymizationAnother else "." }}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
