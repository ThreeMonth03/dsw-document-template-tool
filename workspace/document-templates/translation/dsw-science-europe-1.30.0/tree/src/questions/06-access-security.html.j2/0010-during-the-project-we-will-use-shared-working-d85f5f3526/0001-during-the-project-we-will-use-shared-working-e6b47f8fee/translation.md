# Translation Unit

- Source File: `src/questions/06-access-security.html.j2`
- Wrapper Name: `__tr_block_0009`
- Wrapper Order: `10`
- Wrapper Key: `during-the-project-we-will-use-shared-working-d85f5f3526`
- Unit Key: `during-the-project-we-will-use-shared-working-e6b47f8fee`
- Source Hash: `ec0362a1704f7e826b3c2cd54ad366614c771477`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
During the project we will use shared working space to work with our data{value} that ensures the prevention of complete data loss. / but we will store all essential data elsewhere. {value}And all the data that are stores elsewhere is adequately backed up. / {value}We make (automated) backups of all data stored outside of the working area.
```

### Source (en)

~~~jinja
During the project we will use shared working space to work with our data{{+" "}}
      {%- if sharedWorkspaceReliablePreventLossReply == uuids.sharedReliablePreventLossSufficientAUuid  -%}
        that ensures the prevention of complete data loss.
      {%- elif sharedWorkspaceReliablePreventLossReply == uuids.sharedReliablePreventLossStoredAUuid -%}
        but we will store all essential data elsewhere.
      {%- endif -%}

      {%- set sharedWorkspaceReliableBackupQUuid = [sharedWorkspaceReliableAUuid, uuids.sharedReliableBackupQUuid]|reply_path -%}
      {%- set sharedWorkspaceReliableBackupReply = repliesMap[sharedWorkspaceReliableBackupQUuid]|reply_str_value  -%}
      {%- if sharedWorkspaceReliableBackupReply == uuids.sharedReliableBackupCopyAllSomewhereAUuid -%}
        {{+" "}}And all the data that are stores elsewhere is adequately backed up.
      {%- elif sharedWorkspaceReliableBackupReply == uuids.sharedReliableBackupCopyBackupsAUuid -%}
        {{+" "}}We make (automated) backups of all data stored outside of the working area.
~~~

### Translation (zh_Hant)

~~~jinja

~~~
