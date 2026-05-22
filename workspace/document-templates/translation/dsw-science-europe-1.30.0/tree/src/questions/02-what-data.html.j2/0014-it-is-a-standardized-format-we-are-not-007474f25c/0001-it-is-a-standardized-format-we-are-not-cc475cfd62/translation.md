# Translation Unit

- Source File: `src/questions/02-what-data.html.j2`
- Wrapper Name: `__tr_block_0013`
- Wrapper Order: `14`
- Wrapper Key: `it-is-a-standardized-format-we-are-not-007474f25c`
- Unit Key: `it-is-a-standardized-format-we-are-not-cc475cfd62`
- Source Hash: `70fe1a2c00ae93962f3419c7493748f955bb2f4e`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
It is a standardized format. / We are not using a standardized format because there is no standardized format for this data type. / We are not using a standardized format but it is optimized for processing speed and/or volume. / We are not using a standardized format, because: {formatsWhyNSAnotherReason}. This is a suitable format for long-term archiving. / This is not a suitable format for long-term archiving; however, we plan to convert it to a suitable format before the end of the project. / We are aware that this is not a suitable format for long-term archiving. We will have only a small amount of data stored in this format. / We expect to have {formatsVolumeTotalGB} GB of data in this format. / We expect to have {formatsVolumeFiles} files of average size {formatsVolumeFileGB} GB (i.e. approximately {value} GB in total).
```

### Source (en)

~~~jinja
<p>
            {# standard? #}
            {%- if formatsIsStandardAUuid == uuids.formatsIsStandardYesAUuid %}
              It is a standardized format.
            {%- elif formatsIsStandardAUuid == uuids.formatsIsStandardNoAUuid -%}
              {%- set formatsWhyNonStandardPath = [formatsIsStandardPath, uuids.formatsIsStandardNoAUuid, uuids.formatsWhyNonStandardQUuid]|reply_path -%}
              {%- set formatsWhyNonStandardAUuid = repliesMap[formatsWhyNonStandardPath]|reply_str_value -%}
              {%- if formatsWhyNonStandardAUuid == uuids.formatsWhyNSThereIsNoStandardAUuid %}
                We are not using a standardized format because there is no standardized format for this data type.
              {%- elif formatsWhyNonStandardAUuid == uuids.formatsWhyNSItIsOptimizedAUuid %}
                We are not using a standardized format but it is optimized for processing speed and/or volume.
              {%- elif formatsWhyNonStandardAUuid == uuids.formatsWhyNSAnotherReasonAUuid -%}
                {%- set formatsWhyNSAnotherReasonPath = [formatsWhyNonStandardPath, uuids.formatsWhyNSAnotherReasonAUuid, uuids.formatsWhyNSAnotherReasonQUuid]|reply_path -%}
                {%- set formatsWhyNSAnotherReason = repliesMap[formatsWhyNSAnotherReasonPath]|reply_str_value -%}
                We are not using a standardized format
                {%- if formatsWhyNSAnotherReason -%}
                  , because: {{ formatsWhyNSAnotherReason|capitalize }}
                {%- endif -%}
                .
              {%- endif -%}
            {%- endif -%}
            {# long-term suitable? #}
            {%- if formatsIsLTSuitableAUuid == uuids.formatsIsLTSuitableYesAUuid %}
              This is a suitable format for long-term archiving.
            {%- elif formatsIsLTSuitableAUuid == uuids.formatsIsLTSuitableNoAUuid -%}
              {%- set formatsConvertLTSuitablePath = [formatsIsLTSuitablePath, uuids.formatsIsLTSuitableNoAUuid, uuids.formatsConvertLTSuitableQUuid]|reply_path -%}
              {%- set formatsConvertLTSuitableAUuid = repliesMap[formatsConvertLTSuitablePath]|reply_str_value -%}
              {%- if formatsConvertLTSuitableAUuid == uuids.formatsConvertLTSuitableYesAUuid %}
                This is not a suitable format for long-term archiving; however, we plan to convert it to a suitable format before the end of the project.
              {%- elif formatsConvertLTSuitableAUuid == uuids.formatsConvertLTSuitableNoAUuid %}
                We are aware that this is not a suitable format for long-term archiving.
              {%- endif -%}
            {%- endif -%}
            {# volume #}
            {%- if formatsVolumeAUuid == uuids.formatsVolumeSmallAUuid %}
              We will have only a small amount of data stored in this format.
            {%- elif formatsVolumeAUuid == uuids.formatsVolumeTotalAUuid -%}
              {%- set formatsVolumeTotalGB = repliesMap[[formatsVolumePath, uuids.formatsVolumeTotalAUuid, uuids.formatsVolumeTotalGBQUuid]|reply_path]|reply_str_value -%}
              {%- if formatsVolumeTotalGB %}
                We expect to have {{ formatsVolumeTotalGB }} GB of data in this format.
              {%- endif -%}
            {%- elif formatsVolumeAUuid == uuids.formatsVolumeFileSizeAUuid -%}
              {%- set formatsVolumeFiles = repliesMap[[formatsVolumePath, uuids.formatsVolumeFileSizeAUuid, uuids.formatsVolumeFilesQUuid]|reply_path]|reply_str_value -%}
              {%- set formatsVolumeFileGB = repliesMap[[formatsVolumePath, uuids.formatsVolumeFileSizeAUuid, uuids.formatsVolumeFileGBQUuid]|reply_path]|reply_str_value -%}
              {%- if formatsVolumeFiles and formatsVolumeFileGB %}
                We expect to have {{ formatsVolumeFiles }} files of average size {{ formatsVolumeFileGB }} GB (i.e. approximately {{ (formatsVolumeFiles|int * formatsVolumeFileGB|float)|round(2) }} GB in total).
              {%- endif -%}
            {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
