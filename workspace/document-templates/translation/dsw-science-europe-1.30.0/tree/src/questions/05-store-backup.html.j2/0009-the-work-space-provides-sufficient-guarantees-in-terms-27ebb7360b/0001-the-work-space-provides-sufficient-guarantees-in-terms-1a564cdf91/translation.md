# Translation Unit

- Source File: `src/questions/05-store-backup.html.j2`
- Wrapper Name: `__tr_block_0008`
- Wrapper Order: `9`
- Wrapper Key: `the-work-space-provides-sufficient-guarantees-in-terms-27ebb7360b`
- Unit Key: `the-work-space-provides-sufficient-guarantees-in-terms-1a564cdf91`
- Source Hash: `3d8dd935266fe7e7ce27a2f534b50a9785887e52`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
The work space provides sufficient guarantees in terms of preventing a total loss of data. / All essential data is also stored elsewhere to prevent a total loss of data. Backup of project data that is not in the work space is left to the project participants. / Data is stored only in the work space, therefore additional backup copies of files outside work space are necessary.
```

### Source (en)

~~~jinja
{%- if sharedReliablePreventLossAUuid == uuids.sharedReliablePreventLossSufficientAUuid %}
            The work space provides sufficient guarantees in terms of preventing a total loss of data.
          {%- elif sharedReliablePreventLossAUuid == uuids.sharedReliablePreventLossStoredAUuid %}
            All essential data is also stored elsewhere to prevent a total loss of data.
          {%- endif -%}
          {%- if sharedReliableBackupAUuid == uuids.sharedReliableBackupCopyLeftAUuid %}
            Backup of project data that is not in the work space is left to the project participants.
          {%- elif sharedReliableBackupAUuid == uuids.sharedReliableBackupCopyNoDataAUuid %}
            Data is stored only in the work space, therefore additional backup copies of files outside work space are necessary.
~~~

### Translation (zh_Hant)

~~~jinja

~~~
