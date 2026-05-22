# Translation Unit

- Source File: `src/questions/09-ethical-issues.html.j2`
- Wrapper Name: `__tr_block_0032`
- Wrapper Order: `33`
- Wrapper Key: `the-data-collection-is-subject-to-ethical-legislation-ddb3995857`
- Unit Key: `the-data-collection-is-subject-to-ethical-legislation-4417a63c97`
- Source Hash: `726ae82c92a06ddea6687bedad46f9446bc56662`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
The data collection is subject to ethical legislation. It is not covered by ethical review. / It is covered by ethical review. It does not involve human subjects. / It involves human subjects.
```

### Source (en)

~~~jinja
The data collection is subject to ethical legislation.
          {% if ethLegReviewAUuid == uuids.ethLegReviewNoAUuid %}
          It is not covered by ethical review.
          {% elif ethLegReviewAUuid == uuids.ethLegReviewYesAUuid %}
          It is covered by ethical review.
          {% endif %}
          {% if ethLegHumanAUuid == uuids.ethLegHumanNoAUuid %}
          It does not involve human subjects.
          {% elif ethLegHumanAUuid == uuids.ethLegHumanYesAUuid %}
          It involves human subjects.
~~~

### Translation (zh_Hant)

~~~jinja

~~~
