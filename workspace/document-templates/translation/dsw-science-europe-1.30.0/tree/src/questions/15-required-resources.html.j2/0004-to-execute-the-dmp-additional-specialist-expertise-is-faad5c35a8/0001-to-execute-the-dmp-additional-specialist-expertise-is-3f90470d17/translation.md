# Translation Unit

- Source File: `src/questions/15-required-resources.html.j2`
- Wrapper Name: `__tr_block_0003`
- Wrapper Order: `4`
- Wrapper Key: `to-execute-the-dmp-additional-specialist-expertise-is-faad5c35a8`
- Unit Key: `to-execute-the-dmp-additional-specialist-expertise-is-3f90470d17`
- Source Hash: `aa2f35955557e8b9f6490d73434990f61ae7a110`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
To execute the DMP, additional specialist expertise is required. We will be training existing staff on: {expertiseTrainText}.
```

### Source (en)

~~~jinja
To execute the DMP, additional specialist expertise is required. We will be training existing staff
        {%- set expertiseTrainPath = [expertisePath, uuids.additionalExpertiseYesTrainAUuid, uuids.additionalExpertiseYesTrainTrainingQUuid]|reply_path -%}
        {%- set expertiseTrainText = repliesMap[expertiseTrainPath]|reply_str_value -%}
        {%- if expertiseTrainText %}
          {{" "}}on: {{ expertiseTrainText}}
        {%- endif -%}
        .
~~~

### Translation (zh_Hant)

~~~jinja

~~~
