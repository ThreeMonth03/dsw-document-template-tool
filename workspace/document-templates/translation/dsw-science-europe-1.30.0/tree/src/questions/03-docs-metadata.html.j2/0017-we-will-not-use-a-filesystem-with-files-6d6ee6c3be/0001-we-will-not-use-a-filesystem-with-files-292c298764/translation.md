# Translation Unit

- Source File: `src/questions/03-docs-metadata.html.j2`
- Wrapper Name: `__tr_block_0016`
- Wrapper Order: `17`
- Wrapper Key: `we-will-not-use-a-filesystem-with-files-6d6ee6c3be`
- Unit Key: `we-will-not-use-a-filesystem-with-files-292c298764`
- Source Hash: `42f3cb38ea463921ba2a9749ea09dad4a2e65e6a`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will not use a filesystem with files and folders. / We will use a filesystem with files and folders with the following folder conventions:
```

### Source (en)

~~~jinja
{%- if storageConvFSysAUuid == uuids.storageConvFSysNoAUuid -%}
        We will not use a filesystem with files and folders.
      {%- elif storageConvFSysAUuid == uuids.storageConvFSysYesAUuid -%}
        {%- set scFSysPrefix = [storageConvFSysPath, uuids.storageConvFSysYesAUuid]|reply_path -%}
        {# Folder types #}
        {%- set scFSysSubjFoldersPath = [scFSysPrefix, uuids.scFSysSubjFoldersQUuid]|reply_path -%}
        {%- set scFSysSubjFoldersAUuid = repliesMap[scFSysSubjFoldersPath]|reply_str_value -%}
        {%- set scFSysAnalysisFoldersPath = [scFSysPrefix, uuids.scFSysAnalysisFoldersQUuid]|reply_path -%}
        {%- set scFSysAnalysisFoldersAUuid = repliesMap[scFSysAnalysisFoldersPath]|reply_str_value -%}
        {%- set scFSysWorkflowStepFoldersPath = [scFSysPrefix, uuids.scFSysWorkflowStepFoldersQUuid]|reply_path -%}
        {%- set scFSysWorkflowStepFoldersAUuid = repliesMap[scFSysWorkflowStepFoldersPath]|reply_str_value -%}
        {%- set subjectFolders = scFSysSubjFoldersAUuid == uuids.scFSysSubjFoldersYesAUuid -%}
        {%- set analysisFolders = scFSysAnalysisFoldersAUuid == uuids.scFSysAnalysisFoldersYesAUuid -%}
        {%- set workflowStepFolders = scFSysWorkflowStepFoldersAUuid == uuids.scFSysWorkflowStepFoldersYesAUuid -%}
        {%- set folders = [subjectFolders, analysisFolders, workflowStepFolders] -%}
        {%- if folders|any -%}
          We will use a filesystem with files and folders with the following folder conventions:
~~~

### Translation (zh_Hant)

~~~jinja

~~~
