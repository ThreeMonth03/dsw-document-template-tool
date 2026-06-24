# ruff: noqa: E501
"""Unbalanced exact rewrites for upstream Science Europe templates.

These rules patch fragments that live inside larger unbalanced HTML/Jinja flows
where the generic region scanner cannot safely infer complete boundaries.
Long literals intentionally keep upstream formatting because exact text matching
is part of the reversible transform contract.
"""

from __future__ import annotations

from .rewrite_rules import (
    ReversibleReplacementGroup,
    apply_reversible_replacement_groups,
)


def rewrite_science_europe_unbalanced_html_fragments(source_text: str) -> str:
    """Patch upstream Science Europe sentence fragments that generic HTML cannot see.

    A few upstream fragments live inside large, unbalanced list-item wrappers, so
    the generic paragraph rewriter cannot safely discover their `<p>` boundaries.
    These replacements are still reversible: compacting restores the exact
    upstream text stored in the marker payload.
    """

    return apply_reversible_replacement_groups(
        source_text,
        _build_unbalanced_html_fragment_groups(),
    )


def _build_unbalanced_html_fragment_groups() -> tuple[ReversibleReplacementGroup, ...]:
    """Build exact upstream fragment rewrites for unbalanced Science Europe markup."""

    nref_where_url_if = (
        '{%- if nrefDataWhere.startswith("http://") or '
        'nrefDataWhere.startswith("https://") or '
        'nrefDataWhere.startswith("ftp://") -%}'
    )
    nref_no_reason_other_elif = (
        "{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid "
        "and nrefDataUseNoOtherReasonReply -%}"
    )
    nref_no_cond_sentence = (
        ', but decided not to reuse it{{" "}}because its conditions of use do not allow us '
        "to use it"
    )
    nref_no_reason_other_sentence = (
        ', but decided not to reuse it{{" "}}because: "{{nrefDataUseNoOtherReasonReply}}"'
    )
    nref_where_link = (
        '{{+" "}}available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">'
        "{{ nrefDataWhere }} </a>."
    )
    nref_used_where_url_if = (
        '{%- if nrefDataWhere.startswith("http://") or '
        'nrefDataWhere.startswith("https://") or '
        'nrefDataWhere.startswith("ftp://") -%}'
    )
    nref_used_where_link = (
        '{{" "}} available via:{{" "}}<a href="{{ nrefDataWhere }}" target="_blank">'
        "{{ nrefDataWhere }} </a>."
    )

    personal_data_legal_basis_original = """
                    <p> We are collecting and processing personal data{{+" "}}
                    {%- if personalDataLegalBasisReply == uuids.cpersGdprLegalBasisPublicAUuid -%}
                        based on public interest.</p>
                    {%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisAskAUuid -%}
                        based on subject's consent.</p>
                    {%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisOtherAUuid -%}
                        {%- set personalDataLegalBasisOtherQUuid = [personalDataLegalBasisQUuid, uuids.cpersGdprLegalBasisOtherAUuid, uuids. cpersGdprLegalBasisOtherWhichQUuid ]|reply_path -%}
                        {%- set personalDataLegalBasisOtherReply = repliesMap[personalDataLegalBasisOtherQUuid]|reply_str_value  -%}
                        {%- if personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichContractAUui -%}
                            in order to fulfil contract.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichLegitAUuid -%}
                            based on legitimate interest.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichVitalAUuid -%}
                            based on vital interest.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichLegalAUuid -%}
                            based on legal requirement.</p>
                        {%- endif -%}
                    {%- endif -%}
"""
    personal_data_legal_basis_replacement = """
                    {%- if personalDataLegalBasisReply == uuids.cpersGdprLegalBasisPublicAUuid -%}
                        <p> We are collecting and processing personal data{{+" "}}based on public interest.</p>
                    {%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisAskAUuid -%}
                        <p> We are collecting and processing personal data{{+" "}}based on subject's consent.</p>
                    {%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisOtherAUuid -%}
                        {%- set personalDataLegalBasisOtherQUuid = [personalDataLegalBasisQUuid, uuids.cpersGdprLegalBasisOtherAUuid, uuids. cpersGdprLegalBasisOtherWhichQUuid ]|reply_path -%}
                        {%- set personalDataLegalBasisOtherReply = repliesMap[personalDataLegalBasisOtherQUuid]|reply_str_value  -%}
                        {%- if personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichContractAUui -%}
                            <p> We are collecting and processing personal data{{+" "}}in order to fulfil contract.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichLegitAUuid -%}
                            <p> We are collecting and processing personal data{{+" "}}based on legitimate interest.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichVitalAUuid -%}
                            <p> We are collecting and processing personal data{{+" "}}based on vital interest.</p>
                        {%- elif personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichLegalAUuid -%}
                            <p> We are collecting and processing personal data{{+" "}}based on legal requirement.</p>
                        {%- else -%}
                            <p> We are collecting and processing personal data{%- if false -%}</p>{%- endif -%}
                        {%- endif -%}
                    {%- endif -%}
"""

    copyright_open_reasons_original = """
      {%- if nReasons > 0 -%}
        <p>
        The data cannot become completely open because\x20
        {%- if nReasons == 1 -%}
          {%- if legalReasons %}
            of legal reasons.
          {%- elif businessReasonsPatents %}
            of patent-related business reasons.
          {%- elif businessReasonsOther %}
            of non-patent business reasons{{  ": " ~ notOpenBusinessReasonsOther|dot if notOpenBusinessReasonsOther else "." }}
          {%- elif otherReasonsPapers %}
            we want to publish a paper first.
          {%- elif otherReasonsOther %}
            we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther|dot if notOpenOtherReasonsOther else "." }}
          {%- endif -%}
        {%- else %}
          of:
          <ul>
            {%- if legalReasons %}
              <li>legal reasons</li>
            {%- endif -%}
            {%- if businessReasonsPatents %}
              <li>patent-related business reasons</li>
            {%- elif businessReasonsOther %}
              <li>non-patent business reasons{{ ": " ~ notOpenBusinessReasonsOther if notOpenBusinessReasonsOther else "" }}</li>
            {%- endif -%}
            {%- if otherReasonsPapers %}
              <li>we want to publish a paper first</li>
            {%- elif otherReasonsOther -%}
              <li>we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther if notOpenOtherReasonsOther else "" }}</li>
            {%- endif -%}
          </ul>
        {%- endif -%}
"""
    copyright_open_reasons_replacement = """
      {%- if nReasons > 0 -%}
        <p>
        {%- if nReasons == 1 -%}
          {%- if legalReasons %}
            The data cannot become completely open because of legal reasons.
          {%- elif businessReasonsPatents %}
            The data cannot become completely open because of patent-related business reasons.
          {%- elif businessReasonsOther %}
            The data cannot become completely open because of non-patent business reasons{{  ": " ~ notOpenBusinessReasonsOther|dot if notOpenBusinessReasonsOther else "." }}
          {%- elif otherReasonsPapers %}
            The data cannot become completely open because we want to publish a paper first.
          {%- elif otherReasonsOther %}
            The data cannot become completely open because we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther|dot if notOpenOtherReasonsOther else "." }}
          {%- endif -%}
        {%- else %}
          The data cannot become completely open because of:
          <ul>
            {%- if legalReasons %}
              <li>legal reasons</li>
            {%- endif -%}
            {%- if businessReasonsPatents %}
              <li>patent-related business reasons</li>
            {%- elif businessReasonsOther %}
              <li>non-patent business reasons{{ ": " ~ notOpenBusinessReasonsOther if notOpenBusinessReasonsOther else "" }}</li>
            {%- endif -%}
            {%- if otherReasonsPapers %}
              <li>we want to publish a paper first</li>
            {%- elif otherReasonsOther -%}
              <li>we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther if notOpenOtherReasonsOther else "" }}</li>
            {%- endif -%}
          </ul>
        {%- endif -%}
"""

    measured_reuse_other_field_original = """
                <p>Researchers working in other fields will be interested in re-using this data
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
                {%- if measuredDataReuseOtherFieldHowReply -%}
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
                 {{" "}}because: {{measuredDataReuseOtherFieldHowReply|dot}}</p>
                {%- else -%}
                .
                {%- endif -%}
"""
    measured_reuse_other_field_replacement = """
                {%- if measuredDataReuseOtherFieldHowReply -%}
                <p>Researchers working in other fields will be interested in re-using this data{{" "}}because: {{measuredDataReuseOtherFieldHowReply|dot}}</p>
                {%- else -%}
                <p>Researchers working in other fields will be interested in re-using this data.</p>
                {%- endif -%}
"""

    additional_expertise_train_original = """
    {%- elif expertiseAUuid == uuids.additionalExpertiseYesTrainAUuid -%}
      <p>
        To execute the DMP, additional specialist expertise is required. We will be training existing staff
        {%- set expertiseTrainPath = [expertisePath, uuids.additionalExpertiseYesTrainAUuid, uuids.additionalExpertiseYesTrainTrainingQUuid]|reply_path -%}
        {%- set expertiseTrainText = repliesMap[expertiseTrainPath]|reply_str_value -%}
        {%- if expertiseTrainText %}
          {{" "}}on: {{ expertiseTrainText|markdown }}
        {%- else -%}
          .
        {%- endif -%}
      </p>
"""
    additional_expertise_train_replacement = """
    {%- elif expertiseAUuid == uuids.additionalExpertiseYesTrainAUuid -%}
      {# __tr_branch_sentence_original:PHA-CiAgICAgICAgVG8gZXhlY3V0ZSB0aGUgRE1QLCBhZGRpdGlvbmFsIHNwZWNpYWxpc3QgZXhwZXJ0aXNlIGlzIHJlcXVpcmVkLiBXZSB3aWxsIGJlIHRyYWluaW5nIGV4aXN0aW5nIHN0YWZmCiAgICAgICAgeyUtIHNldCBleHBlcnRpc2VUcmFpblBhdGggPSBbZXhwZXJ0aXNlUGF0aCwgdXVpZHMuYWRkaXRpb25hbEV4cGVydGlzZVllc1RyYWluQVV1aWQsIHV1aWRzLmFkZGl0aW9uYWxFeHBlcnRpc2VZZXNUcmFpblRyYWluaW5nUVV1aWRdfHJlcGx5X3BhdGggLSV9CiAgICAgICAgeyUtIHNldCBleHBlcnRpc2VUcmFpblRleHQgPSByZXBsaWVzTWFwW2V4cGVydGlzZVRyYWluUGF0aF18cmVwbHlfc3RyX3ZhbHVlIC0lfQogICAgICAgIHslLSBpZiBleHBlcnRpc2VUcmFpblRleHQgJX0KICAgICAgICAgIHt7IiAifX1vbjoge3sgZXhwZXJ0aXNlVHJhaW5UZXh0fG1hcmtkb3duIH19CiAgICAgICAgeyUtIGVsc2UgLSV9CiAgICAgICAgICAuCiAgICAgICAgeyUtIGVuZGlmIC0lfQogICAgICA8L3A- #}
      {%- set expertiseTrainPath = [expertisePath, uuids.additionalExpertiseYesTrainAUuid, uuids.additionalExpertiseYesTrainTrainingQUuid]|reply_path -%}
      {%- set expertiseTrainText = repliesMap[expertiseTrainPath]|reply_str_value -%}
      {%- if expertiseTrainText -%}
        <p>To execute the DMP, additional specialist expertise is required. We will be training existing staff on: {{ expertiseTrainText|markdown }}</p>
      {%- else -%}
        <p>To execute the DMP, additional specialist expertise is required. We will be training existing staff.</p>
      {%- endif -%}
      {# __tr_branch_sentence_original:end #}
"""

    reference_data_version_original = """
            {# version #}
            {%- set refDataVersionedPath = [refDataUsedPrefix, uuids.refDataVersionedQUuid]|reply_path -%}
            {%- set refDataVersionedAUuid = repliesMap[refDataVersionedPath]|reply_str_value -%}
            {%- if refDataVersionedAUuid == uuids.refDataVersionedYesAUuid -%}{%- set refDataVersionedWhichPath = [refDataVersionedPath, uuids.refDataVersionedYesAUuid, uuids.refDataVersionedWhichQUuid]|reply_path -%}{%- set refDataVersionedWhich = repliesMap[refDataVersionedWhichPath]|reply_str_value -%}{%- set refDataVersionedChangePath = [refDataVersionedPath, uuids.refDataVersionedYesAUuid, uuids.refDataVersionedChangeQUuid]|reply_path -%}{%- set refDataVersionedChangeAUuid = repliesMap[refDataVersionedChangePath]|reply_str_value -%}{%- if refDataVersionedChangeAUuid == uuids.refDataVersionedChangeStayAUuid %}{%- if refDataVersionedWhich or refDataVersionedChangeAUuid  %}
                <p>
                {% if refDataVersionedWhich -%}
                  We will use the following version of this dataset: {{ refDataVersionedWhich|markdown }}
                {%- endif -%}{{" "}}
                  If a new version becomes available during the project, we will stay with the old version.</p>
              {%- endif -%}
            {%- elif refDataVersionedChangeAUuid == uuids.refDataVersionedChangeNewAUuid %}{%- if refDataVersionedWhich or refDataVersionedChangeAUuid  %}
                <p>
                {% if refDataVersionedWhich -%}
                  We will use the following version of this dataset: {{ refDataVersionedWhich|markdown }}
                {%- endif -%}{{" "}}
                  If a new version becomes available during the project, new analyses will be done with the new version.</p>
              {%- endif -%}
            {%- elif refDataVersionedChangeAUuid == uuids.refDataVersionedChangeAllAUuid %}{%- if refDataVersionedWhich or refDataVersionedChangeAUuid  %}
                <p>
                {% if refDataVersionedWhich -%}
                  We will use the following version of this dataset: {{ refDataVersionedWhich|markdown }}
                {%- endif -%}{{" "}}
                  If a new version becomes available during the project, all analyses will be redone with the new version.</p>
              {%- endif -%}
            {% else %}{%- if refDataVersionedWhich or refDataVersionedChangeAUuid  %}
                <p>
                {% if refDataVersionedWhich -%}
                  We will use the following version of this dataset: {{ refDataVersionedWhich|markdown }}
                {%- endif -%}</p>
              {%- endif -%}
            {%- endif -%}{%- endif -%}

"""
    reference_data_version_replacement = """
            {# version #}
            {%- set refDataVersionedPath = [refDataUsedPrefix, uuids.refDataVersionedQUuid]|reply_path -%}
            {%- set refDataVersionedAUuid = repliesMap[refDataVersionedPath]|reply_str_value -%}
            {%- if refDataVersionedAUuid == uuids.refDataVersionedYesAUuid -%}{%- set refDataVersionedWhichPath = [refDataVersionedPath, uuids.refDataVersionedYesAUuid, uuids.refDataVersionedWhichQUuid]|reply_path -%}{%- set refDataVersionedWhich = repliesMap[refDataVersionedWhichPath]|reply_str_value -%}{%- set refDataVersionedChangePath = [refDataVersionedPath, uuids.refDataVersionedYesAUuid, uuids.refDataVersionedChangeQUuid]|reply_path -%}{%- set refDataVersionedChangeAUuid = repliesMap[refDataVersionedChangePath]|reply_str_value -%}
            {%- if refDataVersionedChangeAUuid == uuids.refDataVersionedChangeStayAUuid -%}
              {%- if refDataVersionedWhich -%}
                <p>We will use the following version of this dataset: {{ refDataVersionedWhich|markdown }} If a new version becomes available during the project, we will stay with the old version.</p>
              {%- else -%}
                <p>If a new version becomes available during the project, we will stay with the old version.</p>
              {%- endif -%}
            {%- elif refDataVersionedChangeAUuid == uuids.refDataVersionedChangeNewAUuid -%}
              {%- if refDataVersionedWhich -%}
                <p>We will use the following version of this dataset: {{ refDataVersionedWhich|markdown }} If a new version becomes available during the project, new analyses will be done with the new version.</p>
              {%- else -%}
                <p>If a new version becomes available during the project, new analyses will be done with the new version.</p>
              {%- endif -%}
            {%- elif refDataVersionedChangeAUuid == uuids.refDataVersionedChangeAllAUuid -%}
              {%- if refDataVersionedWhich -%}
                <p>We will use the following version of this dataset: {{ refDataVersionedWhich|markdown }} If a new version becomes available during the project, all analyses will be redone with the new version.</p>
              {%- else -%}
                <p>If a new version becomes available during the project, all analyses will be redone with the new version.</p>
              {%- endif -%}
            {%- elif refDataVersionedWhich -%}
              <p>We will use the following version of this dataset: {{ refDataVersionedWhich|markdown }}</p>
            {%- endif -%}
            {%- endif -%}

"""

    information_risk_labels_original = """
    {# Extract selected levels for each type #}
    {%- set selected = {
      'loss': risk_levels[risksInfoLossAUuid],
      'leak': risk_levels[risksInfoLeakAUuid],
      'vandalism': risk_levels[risksInfoVandalismAUuid]
    } -%}
"""
    information_risk_labels_replacement = """
    {# Extract selected levels for each type #}
    {%- set selected = {
      '資訊遺失': risk_levels[risksInfoLossAUuid],
      '資訊外洩': risk_levels[risksInfoLeakAUuid],
      '資訊遭竄改': risk_levels[risksInfoVandalismAUuid]
    } -%}
"""

    information_risk_join_original = """
      {%- set risks = (small[:-1]|join(', ') ~ ', and ' ~ small[-1]) if small|length > 1 else small[0] -%}
"""
    information_risk_join_replacement = """
      {%- set risks = small|join('、') -%}
"""
    information_low_risk_join_original = """
      {%- set risks = (low[:-1]|join(', ') ~ ', and ' ~ low[-1]) if low|length > 1 else low[0] -%}
"""
    information_low_risk_join_replacement = """
      {%- set risks = low|join('、') -%}
"""
    information_will_risk_join_original = """
      {%- set risks = (will[:-1]|join(', ') ~ ', and ' ~ will[-1]) if will|length > 1 else will[0] -%}
"""
    information_will_risk_join_replacement = """
      {%- set risks = will|join('、') -%}
"""

    replacements = (
        (personal_data_legal_basis_original, personal_data_legal_basis_replacement),
        (copyright_open_reasons_original, copyright_open_reasons_replacement),
        (measured_reuse_other_field_original, measured_reuse_other_field_replacement),
        (additional_expertise_train_original, additional_expertise_train_replacement),
        (reference_data_version_original, reference_data_version_replacement),
        (information_risk_labels_original, information_risk_labels_replacement),
        (information_risk_join_original, information_risk_join_replacement),
        (information_low_risk_join_original, information_low_risk_join_replacement),
        (information_will_risk_join_original, information_will_risk_join_replacement),
        (
            f"""
         {{{{" "}}}} available via:{{{{" "}}}}
            {nref_used_where_url_if}
              <a href="{{{{ nrefDataWhere }}}}" target="_blank">{{{{ nrefDataWhere }}}} </a>.
            {{%- else -%}}
              {{{{ nrefDataWhere }}}}
            {{%- endif -%}}
""",
            f"""
            {nref_used_where_url_if}
         {nref_used_where_link}
            {{%- else -%}}
         {{{{" "}}}} available via:{{{{" "}}}}{{{{ nrefDataWhere }}}}
            {{%- endif -%}}
""",
        ),
        (
            f"""
          {{{{+" "}}}}available via:{{{{" "}}}}
            {nref_where_url_if}
              <a href="{{{{ rnefDataWhere }}}}" target="_blank">{{{{ nrefDataWhere }}}} </a>.
            {{%- else -%}}
              {{{{ nrefDataWhere }}}}
            {{%- endif -%}}
""",
            f"""
            {nref_where_url_if}
          {nref_where_link}
            {{%- else -%}}
          {{{{+" "}}}}available via:{{{{" "}}}}{{{{ nrefDataWhere }}}}
            {{%- endif -%}}
""",
        ),
        (
            """
                available with{{" "}}
                  {%- if nrefDataConditionsOtherReply -%}
                   following restrictions: "{{nrefDataConditionsOtherReply}}".
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
""",
            """
                  {%- if nrefDataConditionsOtherReply -%}
                available with{{" "}}following restrictions: "{{nrefDataConditionsOtherReply}}".
                  {%- else -%}
                available with{{" "}}restrictions, that will be specified.
                  {%- endif -%}
""",
        ),
        (
            f"""
            , but decided not to reuse it
            {{%- if nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}}
              {{{{" "}}}}because it misses data we need
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}}
              {{{{" "}}}}becauseit misses required aspects
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}}
              {{{{" "}}}}becauseit is not sufficient quality
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}}
              {{{{" "}}}}because its conditions of use do not allow us to use it
            {nref_no_reason_other_elif}
              {{{{" "}}}}because: "{{{{nrefDataUseNoOtherReasonReply}}}}"
            {{%- endif -%}}
            .
""",
            f"""
            {{%- if nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}}
            , but decided not to reuse it{{{{" "}}}}because it misses data we need.
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}}
            , but decided not to reuse it{{{{" "}}}}becauseit misses required aspects.
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}}
            , but decided not to reuse it{{{{" "}}}}becauseit is not sufficient quality.
            {{%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}}
            {nref_no_cond_sentence}.
            {nref_no_reason_other_elif}
            {nref_no_reason_other_sentence}.
            {{%- else -%}}
            , but decided not to reuse it.
            {{%- endif -%}}
""",
        ),
    )

    return (
        ReversibleReplacementGroup(
            "unbalanced_science_europe_html_fragments",
            replacements,
        ),
    )
