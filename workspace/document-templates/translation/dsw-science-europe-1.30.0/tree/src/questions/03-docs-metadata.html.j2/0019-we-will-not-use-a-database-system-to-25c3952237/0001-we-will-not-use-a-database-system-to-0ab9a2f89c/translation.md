# Translation Unit

- Source File: `src/questions/03-docs-metadata.html.j2`
- Wrapper Name: `__tr_block_0018`
- Wrapper Order: `19`
- Wrapper Key: `we-will-not-use-a-database-system-to-25c3952237`
- Unit Key: `we-will-not-use-a-database-system-to-0ab9a2f89c`
- Source Hash: `ca1d37656103ba84fbf9acd95ef2dd91f9f144ea`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will not use a database system to store project data. / We will use a database system to store project data. Data in the database will be read-only. / We will be allowing Create, Update and Delete operations for data in the database. / Modifications will be made by
```

### Source (en)

~~~jinja
{%- if storageConvRelDbAUuid == uuids.storageConvRelDbNoAUuid -%}
        We will not use a database system to store project data.
      {%- elif storageConvRelDbAUuid == uuids.storageConvRelDbYesAUuid -%}
        We will use a database system to store project data.
        {%- set scRelDbHandleChangesPath = [storageConvRelDbPath, uuids.storageConvRelDbYesAUuid, uuids.scRelDbHandleChangesQUuid]|reply_path -%}
        {%- set scRelDbHandleChangesAUuid = repliesMap[scRelDbHandleChangesPath]|reply_str_value -%}
        {%- if scRelDbHandleChangesAUuid == uuids.scRelDbReadOnlyAnswerUuid %}
          Data in the database will be read-only.
        {%- elif scRelDbHandleChangesAUuid == uuids.scRelDbCrudAnswerUuid %}
          We will be allowing Create, Update and Delete operations for data in the database.
        {%- elif scRelDbHandleChangesAUuid == uuids.scRelDbExpireAnswerUuid %}
          Modifications will be made by
~~~

### Translation (zh_Hant)

~~~jinja

~~~
