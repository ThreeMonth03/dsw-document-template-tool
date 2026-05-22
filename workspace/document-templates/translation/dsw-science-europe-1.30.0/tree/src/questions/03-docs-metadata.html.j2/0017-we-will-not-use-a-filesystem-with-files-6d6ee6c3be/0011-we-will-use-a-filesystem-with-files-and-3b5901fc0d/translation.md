# Translation Unit

- Source File: `src/questions/03-docs-metadata.html.j2`
- Wrapper Name: `__tr_block_0016`
- Wrapper Order: `17`
- Wrapper Key: `we-will-not-use-a-filesystem-with-files-6d6ee6c3be`
- Unit Key: `we-will-use-a-filesystem-with-files-and-3b5901fc0d`
- Source Hash: `eacc64e9f34039090059b6607f15b0ee68dd7259`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
/ We will use a filesystem with files and folders. We document how we manage file versioning for files and folders. Moreover, we / We have made appointments about naming the files. {appointmentsText}
```

### Source (en)

~~~jinja
{%- else -%}
          We will use a filesystem with files and folders.
        {%- endif -%}
        {# Versioning #}
        {%- set scDocumentVersioningPath = [scFSysPrefix, uuids.scDocumentVersioningQUuid]|reply_path -%}
        {%- set scDocumentVersioningAUuid = repliesMap[scDocumentVersioningPath]|reply_str_value -%}
        {%- if scDocumentVersioningAUuid == uuids.scDocumentVersioningYesAUuid %}
          We document how we manage file versioning for files and folders.
        {%- endif -%}
        {# Other appointments #}
        {%- set scFSysAppointmentsPath = [scFSysPrefix, uuids.scFSysAppointmentsQUuid]|reply_path -%}
        {%- set scFSysAppointments = repliesMap[scFSysAppointmentsPath]|reply_str_value -%}
        {%- if scFSysAppointments %}
          {{ "Moreover, we" if folders|any else "We" }} have made appointments about naming the files. {{ appointmentsText|capitalize|dot }}
        {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
