# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0005`
- Wrapper Order: `6`
- Wrapper Key: `no-name-given-we-will-re-use-this-5abab0cd8f`
- Unit Key: `we-will-use-version-of-this-dataset-if-d86404e10f`
- Source Hash: `2b0b8739357c5bac19c63466497401dda52d56ee`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will use version "{refDataVersionedWhich}" of this dataset. If a new version becomes available during the project, we will stay with the old version. / If a new version becomes available during the project, new analyses will be done with the new version. / If a new version becomes available during the project, all analyses will be redone with the new version.
```

### Source (en)

~~~jinja
<p>
                {% if refDataVersionedWhich -%}
                  We will use version "{{ refDataVersionedWhich }}" of this dataset.
                {%- endif -%}
                {%- if refDataVersionedChangeAUuid == uuids.refDataVersionedChangeStayAUuid %}
                  If a new version becomes available during the project, we will stay with the old version.
                {%- elif refDataVersionedChangeAUuid == uuids.refDataVersionedChangeNewAUuid %}
                  If a new version becomes available during the project, new analyses will be done with the new version.
                {%- elif refDataVersionedChangeAUuid == uuids.refDataVersionedChangeAllAUuid %}
                  If a new version becomes available during the project, all analyses will be redone with the new version.
                {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
