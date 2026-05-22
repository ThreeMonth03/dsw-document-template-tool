# Translation Unit

- Source File: `src/questions/06-access-security.html.j2`
- Wrapper Name: `__tr_block_0010`
- Wrapper Order: `11`
- Wrapper Key: `we-will-be-archiving-data-for-long-term-d3cc95f44c`
- Unit Key: `we-will-be-archiving-data-for-long-term-ad059c9762`
- Source Hash: `f4fa7e0950200e7daaded208a3890f35d1318c45`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will be archiving data for long-term preservation already during our project. The archived data will be changing over time and needs re-archival. This data needs frequent backups and we will rely on these backups in case of recovery from human errors.
```

### Source (en)

~~~jinja
We will be archiving data for long-term preservation already during our project.
      {%- set preservingArchivedDuringReQUuid = [preservingArchivedDuringQUuid, uuids.archivedDuringYesAUuid, uuids.archivedDuringReQUuid]|reply_path  -%}
      {%- set preservingArchivedDuringReReply = repliesMap[preservingArchivedDuringReQUuid]|reply_str_value -%}

      {%- if preservingArchivedDuringReReply == uuids.archivedDuringReYesAUuid -%}
        {{" "}}The archived data will be changing over time and needs re-archival.
        {%- set preservingArchivedDuringRelyQUuid = [preservingArchivedDuringReQUuid, uuids.archivedDuringReYesAUuid, uuids.archivedDuringRelyQUuid]|reply_path -%}
        {%- set preservingArchivedDuringRelyReply = repliesMap[preservingArchivedDuringRelyQUuid]|reply_str_value -%}
        {%- set archivedDuringReFrequentBackupsQUuid = [preservingArchivedDuringReQUuid, uuids.archivedDuringReYesAUuid, uuids.archivedDuringReFrequentBackupsQUuid]|reply_path-%}
        {%- set preservingArchivedDuringReFrequentBackupsReply = repliesMap[archivedDuringReFrequentBackupsQUuid]|reply_str_value -%}
          
        {%- if (preservingArchivedDuringReFrequentBackupsReply == uuids.archivedDuringReFrequentBackupsYesAUuid ) and (preservingArchivedDuringRelyReply == uuids.archivedDuringRelyYesAUuid) -%}
          {{" "}}This data needs frequent backups and we will rely on these backups in case of recovery from human errors.
~~~

### Translation (zh_Hant)

~~~jinja

~~~
