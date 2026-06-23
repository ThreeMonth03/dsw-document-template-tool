"""Exact reversible rewrites for upstream Science Europe templates."""

from __future__ import annotations

from .rewrite_rules import (
    ReversibleReplacementGroup,
    apply_reversible_replacement_groups,
)


def rewrite_science_europe_balanced_source_fragments(source_text: str) -> str:
    """Rewrite exact upstream Science Europe fragments before generic expansion."""

    ref_data_conditions_original = """
            {%- if refDataConditionsReply %}
             <p>This standard reference data are{{+" "}}
              {%- if refDataConditionsReply == uuids.refDataConditionsCC0AUuid -%}
                freely available for any use.
              {%- elif refDataConditionsReply == uuids.refDataConditionsCCBYAUuid -%}
                freely available with obligation to quote the source.
              {%- elif refDataConditionsReply == uuids.refDataConditionsOtherAUuid -%}
                available with {{" "}}
                  {%- if refDataConditionsOtherRepl -%}
                    following restrictions: "{{refDataConditionsOtherRepl}}".
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
              {%- endif -%}
             </p>
            {%- endif -%}
"""
    ref_data_conditions_replacement = """
            {%- if refDataConditionsReply %}
              {%- if refDataConditionsReply == uuids.refDataConditionsCC0AUuid -%}
                <p>This standard reference data are{{+" "}}freely available for any use.</p>
              {%- elif refDataConditionsReply == uuids.refDataConditionsCCBYAUuid -%}
                <p>This standard reference data are{{+" "}}freely available with obligation to quote the source.</p>
              {%- elif refDataConditionsReply == uuids.refDataConditionsOtherAUuid -%}
                {%- if refDataConditionsOtherRepl -%}
                  <p>This standard reference data are{{+" "}}available with following restrictions: "{{refDataConditionsOtherRepl}}".</p>
                {%- else -%}
                  <p>This standard reference data are{{+" "}}available with restrictions, that will be specified.</p>
                {%- endif -%}
              {%- endif -%}
            {%- endif -%}
"""

    ref_data_conditions_markdown_original = """
            {%- set refDataConditions = [refDataUsedPrefix, uuids.refDataConditionsQUuid]|reply_path -%}
            {%- set refDataConditionsReply = repliesMap[refDataConditions]|reply_str_value -%}
            {%- set refDataConditionsOther = [refDataConditions, uuids.refDataConditionsOtherAUuid, uuids.refDataConditionsOtherQUuid]|reply_path -%}
            {%- set refDataConditionsOtherReply = repliesMap[refDataConditionsOther]|reply_str_value -%}
            {%- if refDataConditionsReply %}
             <p>This standard reference data are{{+" "}}
              {%- if refDataConditionsReply == uuids.refDataConditionsCC0AUuid -%}
                freely available for any use.
              {%- elif refDataConditionsReply == uuids.refDataConditionsCCBYAUuid -%}
                freely available with obligation to quote the source.
              {%- elif refDataConditionsReply == uuids.refDataConditionsOtherAUuid -%}
                available with {{" "}}
                  {%- if refDataConditionsOtherReply -%}
                    following restrictions: {{refDataConditionsOtherReply|markdown}}
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
              {%- endif -%}
             </p>
            {%- endif -%}
"""
    ref_data_conditions_markdown_replacement = """
            {%- set refDataConditions = [refDataUsedPrefix, uuids.refDataConditionsQUuid]|reply_path -%}
            {%- set refDataConditionsReply = repliesMap[refDataConditions]|reply_str_value -%}
            {%- set refDataConditionsOther = [refDataConditions, uuids.refDataConditionsOtherAUuid, uuids.refDataConditionsOtherQUuid]|reply_path -%}
            {%- set refDataConditionsOtherReply = repliesMap[refDataConditionsOther]|reply_str_value -%}
            {%- if refDataConditionsReply %}
              {%- if refDataConditionsReply == uuids.refDataConditionsCC0AUuid -%}
                <p>This standard reference data are{{+" "}}freely available for any use.</p>
              {%- elif refDataConditionsReply == uuids.refDataConditionsCCBYAUuid -%}
                <p>This standard reference data are{{+" "}}freely available with obligation to quote the source.</p>
              {%- elif refDataConditionsReply == uuids.refDataConditionsOtherAUuid -%}
                {%- if refDataConditionsOtherReply -%}
                  <p>This standard reference data are{{+" "}}available with following restrictions: {{refDataConditionsOtherReply|markdown}}</p>
                {%- else -%}
                  <p>This standard reference data are{{+" "}}available with restrictions, that will be specified.</p>
                {%- endif -%}
              {%- endif -%}
            {%- endif -%}
"""

    nref_data_conditions_original = """
          {%- if nrefDataConditionsReply %}
            <p>This data are{{+" "}}
            {%- if nrefDataConditionsReply == uuids.nrefDataConditionsCC0AUuid -%}
              freely available for any use.
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsCCBYAUuid -%}
              freely available with obligation to quote the source.
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsOtherAUuid  -%}
              {%- set nrefDataConditionsOther = [nrefDataConditions, uuids.nrefDataConditionsOtherAUuid, uuids.nrefDataConditionsOtherQUuid]|reply_path -%}
              {%- set nrefDataConditionsOtherReply = repliesMap[nrefDataConditionsOther]|reply_str_value -%}
              {%- if nrefDataConditionsOtherReply -%}
                available with{{" "}}
                  {%- if nrefDataConditionsOtherReply -%}
                   following restrictions: "{{nrefDataConditionsOtherReply}}".
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
              {%- endif -%}
            {%- endif -%}
            </p>
          {%- endif -%}
"""
    nref_data_conditions_replacement = """
          {%- if nrefDataConditionsReply %}
            {%- if nrefDataConditionsReply == uuids.nrefDataConditionsCC0AUuid -%}
              <p>This data are{{+" "}}freely available for any use.</p>
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsCCBYAUuid -%}
              <p>This data are{{+" "}}freely available with obligation to quote the source.</p>
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsOtherAUuid  -%}
              {%- set nrefDataConditionsOther = [nrefDataConditions, uuids.nrefDataConditionsOtherAUuid, uuids.nrefDataConditionsOtherQUuid]|reply_path -%}
              {%- set nrefDataConditionsOtherReply = repliesMap[nrefDataConditionsOther]|reply_str_value -%}
              {%- if nrefDataConditionsOtherReply -%}
                <p>This data are{{+" "}}available with following restrictions: "{{nrefDataConditionsOtherReply}}".</p>
              {%- else -%}
                <p>This data are{{+" "}}available with restrictions, that will be specified.</p>
              {%- endif -%}
            {%- endif -%}
          {%- endif -%}
"""

    measured_external_ownership_original = """
              <p>
                This dataset will be collected by an external party.
                {% if mdExternalOwnershipAUuid == uuids.mdExternalOwnershipPartyAUuid -%}
                  The ownership of the resulting data will remain with the external party.
                {%- elif mdExternalOwnershipAUuid == uuids.mdExternalOwnershipPartnersAUuid -%}
                  The project partners acquire full ownership of the data.
                {%- elif mdExternalOwnershipAUuid == uuids.mdExternalOwnershipOtherAUuid -%}
                  {%- set mdExternalOwnershipOtherPath = [mdExternalOwnershipPath, uuids.mdExternalOwnershipOtherAUuid, uuids.mdExternalOwnershipOtherQUuid]|reply_path -%}
                  {%- set mdExternalOwnershipOther = repliesMap[mdExternalOwnershipOtherPath]|reply_str_value -%}
                  {%- if mdExternalOwnershipOther -%}
                    For the ownership of the data we have made the following arrangements: {{ mdExternalOwnershipOther|dot }}
                  {%- endif -%}
                {%- endif -%}
              </p>
"""
    measured_external_ownership_replacement = """
              {%- if mdExternalOwnershipAUuid == uuids.mdExternalOwnershipPartyAUuid -%}
                <p>This dataset will be collected by an external party. The ownership of the resulting data will remain with the external party.</p>
              {%- elif mdExternalOwnershipAUuid == uuids.mdExternalOwnershipPartnersAUuid -%}
                <p>This dataset will be collected by an external party. The project partners acquire full ownership of the data.</p>
              {%- elif mdExternalOwnershipAUuid == uuids.mdExternalOwnershipOtherAUuid -%}
                {%- set mdExternalOwnershipOtherPath = [mdExternalOwnershipPath, uuids.mdExternalOwnershipOtherAUuid, uuids.mdExternalOwnershipOtherQUuid]|reply_path -%}
                {%- set mdExternalOwnershipOther = repliesMap[mdExternalOwnershipOtherPath]|reply_str_value -%}
                {%- if mdExternalOwnershipOther -%}
                  <p>This dataset will be collected by an external party. For the ownership of the data we have made the following arrangements: {{ mdExternalOwnershipOther|dot }}</p>
                {%- else -%}
                  <p>This dataset will be collected by an external party.</p>
                {%- endif -%}
              {%- else -%}
                <p>This dataset will be collected by an external party.</p>
              {%- endif -%}
"""

    nref_personal_legal_basis_original = """
          <p>
            This data include personal data
            {%- set nrefDataPersonalLegalBasis = [nrefDataPersonal, uuids.nrefDataPersonalYesAUuid, uuids.nrefDataPersonalLegalBasisQUuid]|reply_path -%}
            {%- set nrefDataPersonalLegalBasisReply = repliesMap[nrefDataPersonalLegalBasis]|reply_str_value -%}
            {%- if nrefDataPersonalLegalBasisReply -%}
              , legaly based on{{+" "}}
              {%- if nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLegalBasisPubInterestAUuid -%}
                public interest for processing the data under GDPR.
              {%- elif nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLegalBasisConsentAUuid -%}
                consent given by the research subject for processing the data under GDPR
                {%- set nrefDataPersonalLegalBasisReuse = [nrefDataPersonalLegalBasis, uuids.nrefDataPersonalLegalBasisConsentAUuid, uuids.nrefDataPersonalLegalBasisConsentReuseQUuid]|reply_path -%}
                {%- set nrefDataPersonalLegalBasisReuseReply = repliesMap[nrefDataPersonalLegalBasisReuse]|reply_str_value -%}
                {%- if nrefDataPersonalLegalBasisReuseReply -%}
                  , which{{+" "}}
                  {%- if nrefDataPersonalLegalBasisReuseReply == uuids.nrefDataPersonalLegalBasisConsentReuseYesAUuid -%}
                    covers also our reuse.
                  {%- elif nrefDataPersonalLegalBasisReuseReply == uuids.nrefDataPersonalLegalBasisConsentReuseNoAUuid -%}
                    does not cover our reuse; therefore, new consent will be needed.
                  {%- endif -%}
                {%- else -%}
                .
                {%- endif -%}
              {%- elif nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLebalBasisOtherAUuid -%}
                {%- set nrefDataPersonalLegalBasisOther = [nrefDataPersonalLegalBasis, uuids.nrefDataPersonalLebalBasisOtherAUuid, uuids.nrefDataPersonalLegalBasisOtherQUuid]|reply_path -%}
                {%- set nrefDataPersonalLegalBasisOtherReply = repliesMap[nrefDataPersonalLegalBasisOther]|reply_str_value -%}
                {%- if nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherLegalAUuid -%}
                  a legal requirement (meaning a legal obligation to do this data processing).
                {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherVitalAUuid -%}
                  a vital interest (meaning it needs to be done to protect the vital interests of the data subject).
                {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherLegitAUuid -%}
                  a legitimate interest (meaning data subjects all expect us to do this data processing because of who we are).
                {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherContractAUuid -%}
                  a requirement to fulfill our contract with the data subjects.
                {%- endif -%}
              {%- endif -%} 
            {%- endif -%}
          </p>
"""
    nref_personal_legal_basis_replacement = """
          {%- set nrefDataPersonalLegalBasis = [nrefDataPersonal, uuids.nrefDataPersonalYesAUuid, uuids.nrefDataPersonalLegalBasisQUuid]|reply_path -%}
          {%- set nrefDataPersonalLegalBasisReply = repliesMap[nrefDataPersonalLegalBasis]|reply_str_value -%}
          {%- if nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLegalBasisPubInterestAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}public interest for processing the data under GDPR.</p>
          {%- elif nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLegalBasisConsentAUuid -%}
            {%- set nrefDataPersonalLegalBasisReuse = [nrefDataPersonalLegalBasis, uuids.nrefDataPersonalLegalBasisConsentAUuid, uuids.nrefDataPersonalLegalBasisConsentReuseQUuid]|reply_path -%}
            {%- set nrefDataPersonalLegalBasisReuseReply = repliesMap[nrefDataPersonalLegalBasisReuse]|reply_str_value -%}
            {%- if nrefDataPersonalLegalBasisReuseReply == uuids.nrefDataPersonalLegalBasisConsentReuseYesAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}consent given by the research subject for processing the data under GDPR, which{{+" "}}covers also our reuse.</p>
            {%- elif nrefDataPersonalLegalBasisReuseReply == uuids.nrefDataPersonalLegalBasisConsentReuseNoAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}consent given by the research subject for processing the data under GDPR, which{{+" "}}does not cover our reuse; therefore, new consent will be needed.</p>
            {%- else -%}
              <p>This data include personal data, legaly based on{{+" "}}consent given by the research subject for processing the data under GDPR.</p>
            {%- endif -%}
          {%- elif nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLebalBasisOtherAUuid -%}
            {%- set nrefDataPersonalLegalBasisOther = [nrefDataPersonalLegalBasis, uuids.nrefDataPersonalLebalBasisOtherAUuid, uuids.nrefDataPersonalLegalBasisOtherQUuid]|reply_path -%}
            {%- set nrefDataPersonalLegalBasisOtherReply = repliesMap[nrefDataPersonalLegalBasisOther]|reply_str_value -%}
            {%- if nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherLegalAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}a legal requirement (meaning a legal obligation to do this data processing).</p>
            {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherVitalAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}a vital interest (meaning it needs to be done to protect the vital interests of the data subject).</p>
            {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherLegitAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}a legitimate interest (meaning data subjects all expect us to do this data processing because of who we are).</p>
            {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherContractAUuid -%}
              <p>This data include personal data, legaly based on{{+" "}}a requirement to fulfill our contract with the data subjects.</p>
            {%- else -%}
              <p>This data include personal data.</p>
            {%- endif -%}
          {%- else -%}
            <p>This data include personal data.</p>
          {%- endif -%}
"""

    computer_readable_original = """
    {%- if dataCompReadReply == uuids.dataCompReadYesAUuid -%}
      <p>We will need to (re-)made the data into computer readable form before their using

      {%- set dataCompReadItself = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadItselfQUuid]|reply_path -%}
      {%- set dataCompReadItselfReply = repliesMap[dataCompReadItself]|reply_str_value -%}
      {%- set dataCompReadOthers = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadOthersQUuid]|reply_path  -%}
      {%- set dataCompReadOthersReply = repliesMap[dataCompReadOthers]|reply_str_value -%}

      {%- if dataCompReadItselfReply -%}
        {%- if dataCompReadItselfReply == uuids.dataCompReadItselfYesAUuid -%}
          {{+" "}}and we will make this computer readable form available to others through a standard repository
        {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfYesOtherAUuid -%} 
          {{+" "}}and we will make this computer readable form available to others
        {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfNoAUuid -%}
          {{+" "}}but we won't make this computer readable form available to others
        {%- endif -%}
      {%- endif -%}
      .

      {%- if dataCompReadOthersReply -%}
        {%- if dataCompReadOthersReply == uuids.dataCompReadOthersYesAUuid %}
            We will provide machine readable, standardized metadata to others
            {%- set dataCompReadWhichMetadataStandardPath = [dataCompReadOthers, uuids.dataCompReadOthersYesAUuid, uuids.dataCompReadOthersYesStandardsQUuid]|reply_path -%}
            {%- set dataCompReadMetadataStandardItems =  repliesMap[dataCompReadWhichMetadataStandardPath]|reply_items -%}
            {%- if dataCompReadMetadataStandardItems|length  > 0 -%}
              {{+" "}}and we will use following Metadata Standards:{{+" "}}
                {%- for dataCompReadMetadataStandardItem in dataCompReadMetadataStandardItems -%}
                  {%- set dataCompReadMetadataStandardPrefix = [dataCompReadWhichMetadataStandardPath, dataCompReadMetadataStandardItem]|reply_path -%}
                  {%- set dataCompReadMetadataStandard = [dataCompReadMetadataStandardPrefix, uuids.dataCompReadOthersYesStandardQUuid]|reply_path -%}
                  {%- set dataCompReadMetadataStandardReply = repliesMap[dataCompReadMetadataStandard] -%}
                  {{ macros.integrationFairSharing(dataCompReadMetadataStandardReply) }}{{ ", " if not loop.last else "." }}
                {%- endfor -%}
            {%- else -%}
            .
            {%- endif -%}

        {%- endif -%}
          
      {%- endif -%}
      </p>
    {%- endif -%}
"""
    computer_readable_replacement = """
    {%- if dataCompReadReply == uuids.dataCompReadYesAUuid -%}
      <p>
      {%- set dataCompReadItself = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadItselfQUuid]|reply_path -%}
      {%- set dataCompReadItselfReply = repliesMap[dataCompReadItself]|reply_str_value -%}
      {%- set dataCompReadOthers = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadOthersQUuid]|reply_path  -%}
      {%- set dataCompReadOthersReply = repliesMap[dataCompReadOthers]|reply_str_value -%}

      {%- if dataCompReadItselfReply == uuids.dataCompReadItselfYesAUuid -%}
        We will need to (re-)made the data into computer readable form before their using{{+" "}}and we will make this computer readable form available to others through a standard repository.
      {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfYesOtherAUuid -%}
        We will need to (re-)made the data into computer readable form before their using{{+" "}}and we will make this computer readable form available to others.
      {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfNoAUuid -%}
        We will need to (re-)made the data into computer readable form before their using{{+" "}}but we won't make this computer readable form available to others.
      {%- else -%}
        We will need to (re-)made the data into computer readable form before their using.
      {%- endif -%}

      {%- if dataCompReadOthersReply == uuids.dataCompReadOthersYesAUuid %}
        {%- set dataCompReadWhichMetadataStandardPath = [dataCompReadOthers, uuids.dataCompReadOthersYesAUuid, uuids.dataCompReadOthersYesStandardsQUuid]|reply_path -%}
        {%- set dataCompReadMetadataStandardItems =  repliesMap[dataCompReadWhichMetadataStandardPath]|reply_items -%}
        {%- if dataCompReadMetadataStandardItems|length  > 0 -%}
          {{+" "}}We will provide machine readable, standardized metadata to others{{+" "}}and we will use following Metadata Standards:{{+" "}}
          {%- for dataCompReadMetadataStandardItem in dataCompReadMetadataStandardItems -%}
            {%- set dataCompReadMetadataStandardPrefix = [dataCompReadWhichMetadataStandardPath, dataCompReadMetadataStandardItem]|reply_path -%}
            {%- set dataCompReadMetadataStandard = [dataCompReadMetadataStandardPrefix, uuids.dataCompReadOthersYesStandardQUuid]|reply_path -%}
            {%- set dataCompReadMetadataStandardReply = repliesMap[dataCompReadMetadataStandard] -%}
            {{ macros.integrationFairSharing(dataCompReadMetadataStandardReply) }}{{ ", " if not loop.last else "." }}
          {%- endfor -%}
        {%- else -%}
          {{+" "}}We will provide machine readable, standardized metadata to others.
        {%- endif -%}
      {%- endif -%}
      </p>
    {%- endif -%}
"""

    ref_data_used_identification_original = """
            <p>We will re-use this standard reference data
            {%- if refDataWhere -%}
              {{" "}}available via:{{" "}}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                <a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
              {%- else -%}
                {{ refDataWhere }}
             {%- endif -%}
            {%- endif -%}
    
            {# usage #}
            {%- set refDataUsageQ = [ refDataUsedPrefix, uuids.refDataUsageQUuid]|reply_path -%}
            {%- set refDataUsageReply = repliesMap[refDataUsageQ]|reply_str_value  -%}
            {%- if refDataUsageReply -%}
                {{+" "}}in order to "{{ refDataUsageReply}}"
            {%- endif -%}
            .</p>
"""
    ref_data_used_identification_replacement = """
            {# usage #}
            {%- set refDataUsageQ = [ refDataUsedPrefix, uuids.refDataUsageQUuid]|reply_path -%}
            {%- set refDataUsageReply = repliesMap[refDataUsageQ]|reply_str_value  -%}
            {%- if refDataWhere -%}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                {%- if refDataUsageReply -%}
                  <p>We will re-use this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>{{+" "}}in order to "{{ refDataUsageReply}}".</p>
                {%- else -%}
                  <p>We will re-use this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.</p>
                {%- endif -%}
              {%- else -%}
                {%- if refDataUsageReply -%}
                  <p>We will re-use this standard reference data available via:{{" "}}{{ refDataWhere }}{{+" "}}in order to "{{ refDataUsageReply}}".</p>
                {%- else -%}
                  <p>We will re-use this standard reference data available via:{{" "}}{{ refDataWhere }}.</p>
                {%- endif -%}
              {%- endif -%}
            {%- elif refDataUsageReply -%}
              <p>We will re-use this standard reference data in order to "{{ refDataUsageReply}}".</p>
            {%- else -%}
              <p>We will re-use this standard reference data.</p>
            {%- endif -%}
"""

    ref_data_used_identification_markdown_original = (
        """
            <p>We will re-use this standard reference data
            {%- if refDataWhere -%}
              {{" "}}available via:{{" "}}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                <a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
              {%- else -%}
                {{ refDataWhere }}
             {%- endif -%}
            {%- endif -%}
"""
        "    \n"
        """            {# usage #}
            {%- set refDataUsageQ = [ refDataUsedPrefix, uuids.refDataUsageQUuid]|reply_path -%}
            {%- set refDataUsageReply = repliesMap[refDataUsageQ]|reply_str_value  -%}
            {%- if refDataUsageReply -%}
                {{+" "}}in order to {{ refDataUsageReply|markdown }}
            {%- else -%}.
            {%- endif -%}
            </p>
"""
    )
    ref_data_used_identification_markdown_replacement = """
            {# usage #}
            {%- set refDataUsageQ = [ refDataUsedPrefix, uuids.refDataUsageQUuid]|reply_path -%}
            {%- set refDataUsageReply = repliesMap[refDataUsageQ]|reply_str_value  -%}
            {%- if refDataWhere -%}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                {%- if refDataUsageReply -%}
                  <p>We will re-use this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>{{+" "}}in order to {{ refDataUsageReply|markdown }}</p>
                {%- else -%}
                  <p>We will re-use this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.</p>
                {%- endif -%}
              {%- else -%}
                {%- if refDataUsageReply -%}
                  <p>We will re-use this standard reference data available via:{{" "}}{{ refDataWhere }}{{+" "}}in order to {{ refDataUsageReply|markdown }}</p>
                {%- else -%}
                  <p>We will re-use this standard reference data available via:{{" "}}{{ refDataWhere }}.</p>
                {%- endif -%}
              {%- endif -%}
            {%- elif refDataUsageReply -%}
              <p>We will re-use this standard reference data in order to {{ refDataUsageReply|markdown }}</p>
            {%- else -%}
              <p>We will re-use this standard reference data.</p>
            {%- endif -%}
"""

    nref_data_used_identification_original = """
          <p>We will re-use this non-referece data 
          {%- if nrefDataWhere -%}
         {{" "}} available via:{{" "}}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              <a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
            {%- else -%}
              {{ nrefDataWhere }}
            {%- endif -%}
          {%- endif -%}
    
          {# usage #}
          {%- set nrefDataUsageQ = [nrefDataUsedPrefix, uuids.nrefDataUsageQUuid]|reply_path  -%}
          {%- set nrefDataUsageReply = repliesMap[nrefDataUsageQ]|reply_str_value -%}
          {%- if nrefDataUsageReply -%}
            {{+" "}}in order to "{{ nrefDataUsageReply}}"
          {%- endif -%}
          .</p>
"""
    nref_data_used_identification_replacement = """
          {# usage #}
          {%- set nrefDataUsageQ = [nrefDataUsedPrefix, uuids.nrefDataUsageQUuid]|reply_path  -%}
          {%- set nrefDataUsageReply = repliesMap[nrefDataUsageQ]|reply_str_value -%}
          {%- if nrefDataWhere -%}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              {%- if nrefDataUsageReply -%}
                <p>We will re-use this non-referece data available via:{{" "}}<a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>{{+" "}}in order to "{{ nrefDataUsageReply}}".</p>
              {%- else -%}
                <p>We will re-use this non-referece data available via:{{" "}}<a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.</p>
              {%- endif -%}
            {%- else -%}
              {%- if nrefDataUsageReply -%}
                <p>We will re-use this non-referece data available via:{{" "}}{{ nrefDataWhere }}{{+" "}}in order to "{{ nrefDataUsageReply}}".</p>
              {%- else -%}
                <p>We will re-use this non-referece data available via:{{" "}}{{ nrefDataWhere }}.</p>
              {%- endif -%}
            {%- endif -%}
          {%- elif nrefDataUsageReply -%}
            <p>We will re-use this non-referece data in order to "{{ nrefDataUsageReply}}".</p>
          {%- else -%}
            <p>We will re-use this non-referece data.</p>
          {%- endif -%}
"""

    nref_data_used_identification_markdown_original = (
        """
          <p>We will re-use this non-referece data"""
        " \n"
        """          {%- if nrefDataWhere -%}
         {{" "}} available via:{{" "}}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              <a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
            {%- else -%}
              {{ nrefDataWhere }}
            {%- endif -%}
          {%- endif -%}
"""
        "    \n"
        """          {# usage #}
          {%- set nrefDataUsageQ = [nrefDataUsedPrefix, uuids.nrefDataUsageQUuid]|reply_path  -%}
          {%- set nrefDataUsageReply = repliesMap[nrefDataUsageQ]|reply_str_value -%}
          {%- if nrefDataUsageReply -%}
            {{+" "}}in order to {{ nrefDataUsageReply|markdown }}
          {%- endif -%}
          .</p>
"""
    )
    nref_data_used_identification_markdown_replacement = """
          {# usage #}
          {%- set nrefDataUsageQ = [nrefDataUsedPrefix, uuids.nrefDataUsageQUuid]|reply_path  -%}
          {%- set nrefDataUsageReply = repliesMap[nrefDataUsageQ]|reply_str_value -%}
          {%- if nrefDataWhere -%}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              {%- if nrefDataUsageReply -%}
                <p>We will re-use this non-referece data available via:{{" "}}<a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>{{+" "}}in order to {{ nrefDataUsageReply|markdown }}.</p>
              {%- else -%}
                <p>We will re-use this non-referece data available via:{{" "}}<a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.</p>
              {%- endif -%}
            {%- else -%}
              {%- if nrefDataUsageReply -%}
                <p>We will re-use this non-referece data available via:{{" "}}{{ nrefDataWhere }}{{+" "}}in order to {{ nrefDataUsageReply|markdown }}.</p>
              {%- else -%}
                <p>We will re-use this non-referece data available via:{{" "}}{{ nrefDataWhere }}.</p>
              {%- endif -%}
            {%- endif -%}
          {%- elif nrefDataUsageReply -%}
            <p>We will re-use this non-referece data in order to {{ nrefDataUsageReply|markdown }}.</p>
          {%- else -%}
            <p>We will re-use this non-referece data.</p>
          {%- endif -%}
"""

    nref_data_used_identification_rnef_link_original = """
          <p>We will re-use this non-referece data 
          {%- if nrefDataWhere -%}
         {{" "}} available via:{{" "}}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              <a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
            {%- else -%}
              {{ nrefDataWhere }}
            {%- endif -%}
          {%- endif -%}
    
          {# usage #}
          {%- set nrefDataUsageQ = [nrefDataUsedPrefix, uuids.nrefDataUsageQUuid]|reply_path  -%}
          {%- set nrefDataUsageReply = repliesMap[nrefDataUsageQ]|reply_str_value -%}
          {%- if nrefDataUsageReply -%}
            {{+" "}}in order to "{{ nrefDataUsageReply}}"
          {%- endif -%}
          .</p>
"""
    nref_data_used_identification_rnef_link_replacement = """
          {# usage #}
          {%- set nrefDataUsageQ = [nrefDataUsedPrefix, uuids.nrefDataUsageQUuid]|reply_path  -%}
          {%- set nrefDataUsageReply = repliesMap[nrefDataUsageQ]|reply_str_value -%}
          {%- if nrefDataWhere -%}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              {%- if nrefDataUsageReply -%}
                <p>We will re-use this non-referece data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>{{+" "}}in order to "{{ nrefDataUsageReply}}".</p>
              {%- else -%}
                <p>We will re-use this non-referece data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.</p>
              {%- endif -%}
            {%- else -%}
              {%- if nrefDataUsageReply -%}
                <p>We will re-use this non-referece data available via:{{" "}}{{ nrefDataWhere }}{{+" "}}in order to "{{ nrefDataUsageReply}}".</p>
              {%- else -%}
                <p>We will re-use this non-referece data available via:{{" "}}{{ nrefDataWhere }}.</p>
              {%- endif -%}
            {%- endif -%}
          {%- elif nrefDataUsageReply -%}
            <p>We will re-use this non-referece data in order to "{{ nrefDataUsageReply}}".</p>
          {%- else -%}
            <p>We will re-use this non-referece data.</p>
          {%- endif -%}
"""

    nref_data_complete_original = """
          {%- if nrefDataCompleteReply -%}
            <p>We will use{{+" "}}
            {%- if nrefDataCompleteReply == uuids.nrefDataCompleteUseAUuid -%}
              the complete data set. 
            {%- elif nrefDataCompleteReply == uuids.nrefDataCompleteDocumentAUuid -%}
              only subset of data and we will select it by filtering and/or selection (which will be documented).
            {%- elif nrefDataCompleteReply == uuids.nrefDataCompleteSubsetAUuid -%}
              only selected subset of data, which will be available together with our results.
            {%- endif -%}
            </p>
          {%- endif -%}
"""
    nref_data_complete_replacement = """
          {%- if nrefDataCompleteReply == uuids.nrefDataCompleteUseAUuid -%}
            <p>We will use{{+" "}}the complete data set.</p>
          {%- elif nrefDataCompleteReply == uuids.nrefDataCompleteDocumentAUuid -%}
            <p>We will use{{+" "}}only subset of data and we will select it by filtering and/or selection (which will be documented).</p>
          {%- elif nrefDataCompleteReply == uuids.nrefDataCompleteSubsetAUuid -%}
            <p>We will use{{+" "}}only selected subset of data, which will be available together with our results.</p>
          {%- endif -%}
"""

    nref_data_fixed_original = """
          {%- if nrefDataFixedReply %}
            <p>This data{{+" "}}
            {%- if nrefDataFixedReply == uuids.nrefDataFixedFixedAUuid -%}
              are fixed, therefore will not influence reproducibility of our results.
            {%- elif nrefDataFixedReply == uuids.nrefDataFixedChangeAUuid -%}
              may change in the future, which might influence reproducibility of our results.
            {%- endif -%}
            </p>
          {%- endif -%}
"""
    nref_data_fixed_replacement = """
          {%- if nrefDataFixedReply == uuids.nrefDataFixedFixedAUuid %}
            <p>This data{{+" "}}are fixed, therefore will not influence reproducibility of our results.</p>
          {%- elif nrefDataFixedReply == uuids.nrefDataFixedChangeAUuid -%}
            <p>This data{{+" "}}may change in the future, which might influence reproducibility of our results.</p>
          {%- endif -%}
"""

    computer_readable_standardised_list_original = """
    {%- if dataCompReadReply == uuids.dataCompReadYesAUuid -%}
      <p>We will need to (re-)made the data into computer readable form before their using

      {%- set dataCompReadItself = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadItselfQUuid]|reply_path -%}
      {%- set dataCompReadItselfReply = repliesMap[dataCompReadItself]|reply_str_value -%}
      {%- set dataCompReadOthers = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadOthersQUuid]|reply_path  -%}
      {%- set dataCompReadOthersReply = repliesMap[dataCompReadOthers]|reply_str_value -%}

      {%- if dataCompReadItselfReply -%}
        {%- if dataCompReadItselfReply == uuids.dataCompReadItselfYesAUuid -%}
          {{+" "}}and we will make this computer readable form available to others throught a standard repository
        {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfYesOtherAUuid -%} 
          {{+" "}}and we will make this computer readable form available to others
        {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfNoAUuid -%}
          {{+" "}}but we won't make this computer readable form available to others
        {%- endif -%}
      {%- endif -%}
      .

      {%- if dataCompReadOthersReply -%}
        {%- if dataCompReadOthersReply == uuids.dataCompReadOthersYesAUuid %}
            We will provide machine readable, standardised metadata to others
            {%- set dataCompReadWhichMetadataStandardPath = [dataCompReadOthers, uuids.dataCompReadOthersYesAUuid, uuids.dataCompReadOthersYesStandardsQUuid]|reply_path -%}
            {%- set dataCompReadMetadataStandardItems =  repliesMap[dataCompReadWhichMetadataStandardPath]|reply_items -%}
            {%- if dataCompReadMetadataStandardItems|length  > 0 -%}
              {{+" "}}and we will use following Metadata Standards:
              <ul>
                {%- for dataCompReadMetadataStandardItem in dataCompReadMetadataStandardItems -%}
                  {%- set  dataCompReadMetadataStandardPrefix = [dataCompReadWhichMetadataStandardPath,dataCompReadMetadataStandardItem ]|reply_path -%}
                  {%- set dataCompReadMetadataStandard = [dataCompReadMetadataStandardPrefix, uuids.dataCompReadOthersYesStandardQUuid]|reply_path -%}
                  {%- set dataCompReadMetadataStandardReply = repliesMap[dataCompReadMetadataStandard] -%}
                  {{macros.integrationValue(dataCompReadMetadataStandardReply)}}
                {%- endfor -%}
              </ul>
            {%- else -%}
            .
            {%- endif -%}

        {%- endif -%}
          
      {%- endif -%}
      </p>
    {%- endif -%}
"""
    computer_readable_standardised_list_replacement = """
    {%- if dataCompReadReply == uuids.dataCompReadYesAUuid -%}
      <p>
      {%- set dataCompReadItself = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadItselfQUuid]|reply_path -%}
      {%- set dataCompReadItselfReply = repliesMap[dataCompReadItself]|reply_str_value -%}
      {%- set dataCompReadOthers = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadOthersQUuid]|reply_path  -%}
      {%- set dataCompReadOthersReply = repliesMap[dataCompReadOthers]|reply_str_value -%}

      {%- if dataCompReadItselfReply == uuids.dataCompReadItselfYesAUuid -%}
        We will need to (re-)made the data into computer readable form before their using{{+" "}}and we will make this computer readable form available to others throught a standard repository.
      {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfYesOtherAUuid -%}
        We will need to (re-)made the data into computer readable form before their using{{+" "}}and we will make this computer readable form available to others.
      {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfNoAUuid -%}
        We will need to (re-)made the data into computer readable form before their using{{+" "}}but we won't make this computer readable form available to others.
      {%- else -%}
        We will need to (re-)made the data into computer readable form before their using.
      {%- endif -%}

      {%- if dataCompReadOthersReply == uuids.dataCompReadOthersYesAUuid %}
        {%- set dataCompReadWhichMetadataStandardPath = [dataCompReadOthers, uuids.dataCompReadOthersYesAUuid, uuids.dataCompReadOthersYesStandardsQUuid]|reply_path -%}
        {%- set dataCompReadMetadataStandardItems =  repliesMap[dataCompReadWhichMetadataStandardPath]|reply_items -%}
        {%- if dataCompReadMetadataStandardItems|length  > 0 -%}
          {{+" "}}We will provide machine readable, standardised metadata to others{{+" "}}and we will use following Metadata Standards:
          <ul>
            {%- for dataCompReadMetadataStandardItem in dataCompReadMetadataStandardItems -%}
              {%- set  dataCompReadMetadataStandardPrefix = [dataCompReadWhichMetadataStandardPath,dataCompReadMetadataStandardItem ]|reply_path -%}
              {%- set dataCompReadMetadataStandard = [dataCompReadMetadataStandardPrefix, uuids.dataCompReadOthersYesStandardQUuid]|reply_path -%}
              {%- set dataCompReadMetadataStandardReply = repliesMap[dataCompReadMetadataStandard] -%}
              {{macros.integrationValue(dataCompReadMetadataStandardReply)}}
            {%- endfor -%}
          </ul>
        {%- else -%}
          {{+" "}}We will provide machine readable, standardised metadata to others.
        {%- endif -%}
      {%- endif -%}
      </p>
    {%- endif -%}
"""
    computer_readable_standardized_list_original = (
        computer_readable_standardised_list_original.replace(
            "standardised", "standardized"
        ).replace("throught", "through")
    )
    computer_readable_standardized_list_replacement = (
        computer_readable_standardised_list_replacement.replace(
            "standardised", "standardized"
        ).replace("throught", "through")
    )

    ref_data_not_used_identification_original = """
            <p> We considered reusing this standard reference data
            {%- if refDataWhere -%}
            {{" "}}available via:{{" "}}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                <a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
              {%- else -%}
                {{ refDataWhere}}
              {%- endif -%}
            {%- endif -%}

            {# no usage reason #}
            {%- if refDataUseNoReply -%}
              , but decided not to re-use it
              {%- if refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
                {{" "}}because it misses data we need
              {%- elif refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
                {{" "}}because it misses required aspects
              {%- elif refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
                {{" "}}because it is not sufficient quality
              {%- elif refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
                {{" "}}because its conditions of use do not allow us to use it
              {%- elif refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
                {{" "}}because: "{{refDataUseNoOtherReasonReply}}"
              {%- endif -%}
              .
            {%- else -%}
            . </p>
            {%- endif -%}
"""
    ref_data_not_used_identification_replacement = """
            <p>
            {# no usage reason #}
            {%- if refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it{{" "}}because it misses data we need.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it{{" "}}because it misses required aspects.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it{{" "}}because it is not sufficient quality.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it{{" "}}because its conditions of use do not allow us to use it.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it{{" "}}because: "{{refDataUseNoOtherReasonReply}}".
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it{{" "}}because it misses data we need.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it{{" "}}because it misses required aspects.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it{{" "}}because it is not sufficient quality.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it{{" "}}because its conditions of use do not allow us to use it.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it{{" "}}because: "{{refDataUseNoOtherReasonReply}}".
            {%- elif refDataWhere and refDataUseNoReply -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it.
            {%- elif refDataWhere -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}.
            {%- elif refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it{{" "}}because it misses data we need.
            {%- elif refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it{{" "}}because it misses required aspects.
            {%- elif refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it{{" "}}because it is not sufficient quality.
            {%- elif refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it{{" "}}because its conditions of use do not allow us to use it.
            {%- elif refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
              We considered reusing this standard reference data, but decided not to re-use it{{" "}}because: "{{refDataUseNoOtherReasonReply}}".
            {%- elif refDataUseNoReply -%}
              We considered reusing this standard reference data, but decided not to re-use it.
            {%- else -%}
              We considered reusing this standard reference data.
            {%- endif -%}
            </p>
"""

    ref_data_not_used_identification_markdown_original = """
            <p> We considered reusing this standard reference data
            {%- if refDataWhere -%}
            {{" "}}available via:{{" "}}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                <a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
              {%- else -%}
                {{ refDataWhere}}
              {%- endif -%}
            {%- endif -%}

            {# no usage reason #}
            {%- if refDataUseNoReply -%}
              , but decided not to re-use it
              {%- if refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
                {{" "}}because it misses data we need.
              {%- elif refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
                {{" "}}because it misses required aspects.
              {%- elif refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
                {{" "}}because it is not sufficient quality.
              {%- elif refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
                {{" "}}because its conditions of use do not allow us to use it.
              {%- elif refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
                {{" "}}because: {{refDataUseNoOtherReasonReply|markdown}}
              {%- else -%}.
              {%- endif -%}
            {%- else -%}
            . </p>
            {%- endif -%}
"""
    ref_data_not_used_identification_markdown_replacement = """
            <p>
            {# no usage reason #}
            {%- if refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it because it misses data we need.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it because it misses required aspects.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it because it is not sufficient quality.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it because its conditions of use do not allow us to use it.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it because: {{refDataUseNoOtherReasonReply|markdown}}
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) and refDataUseNoReply -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>, but decided not to re-use it.
            {%- elif refDataWhere and (refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://")) -%}
              We considered reusing this standard reference data available via:{{" "}}<a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it because it misses data we need.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it because it misses required aspects.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it because it is not sufficient quality.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it because its conditions of use do not allow us to use it.
            {%- elif refDataWhere and refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it because: {{refDataUseNoOtherReasonReply|markdown}}
            {%- elif refDataWhere and refDataUseNoReply -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}, but decided not to re-use it.
            {%- elif refDataWhere -%}
              We considered reusing this standard reference data available via:{{" "}}{{ refDataWhere}}.
            {%- elif refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it because it misses data we need.
            {%- elif refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it because it misses required aspects.
            {%- elif refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it because it is not sufficient quality.
            {%- elif refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
              We considered reusing this standard reference data, but decided not to re-use it because its conditions of use do not allow us to use it.
            {%- elif refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
              We considered reusing this standard reference data, but decided not to re-use it because: {{refDataUseNoOtherReasonReply|markdown}}
            {%- elif refDataUseNoReply -%}
              We considered reusing this standard reference data, but decided not to re-use it.
            {%- else -%}
              We considered reusing this standard reference data.
            {%- endif -%}
            </p>
"""

    nref_data_not_used_identification_original = """
          <p>We considered reusing this non-reference data 
          {%- if nrefDataWhere -%}
          {{+" "}}available via:{{" "}}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              <a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
            {%- else -%}
              {{ nrefDataWhere }}
            {%- endif -%}
          {%- endif -%}

          {# no usage reason #}
          {%- if nrefDataUseNoReply -%}
            , but decided not to reuse it
            {%- if nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
              {{" "}}because it misses data we need
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
              {{" "}}becauseit misses required aspects
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
              {{" "}}becauseit is not sufficient quality
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
              {{" "}}because its conditions of use do not allow us to use it
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
              {{" "}}because: "{{nrefDataUseNoOtherReasonReply}}"
            {%- endif -%}
            .
          {%- else -%}
          .</p>
          {%- endif -%}
"""
    nref_data_not_used_identification_replacement = """
          <p>
          {# no usage reason #}
          {%- if nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it{{" "}}because it misses data we need.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it{{" "}}becauseit misses required aspects.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it{{" "}}becauseit is not sufficient quality.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it{{" "}}because its conditions of use do not allow us to use it.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it{{" "}}because: "{{nrefDataUseNoOtherReasonReply}}".
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it{{" "}}because it misses data we need.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it{{" "}}becauseit misses required aspects.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it{{" "}}becauseit is not sufficient quality.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it{{" "}}because its conditions of use do not allow us to use it.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it{{" "}}because: "{{nrefDataUseNoOtherReasonReply}}".
          {%- elif nrefDataWhere and nrefDataUseNoReply -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it.
          {%- elif nrefDataWhere -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it{{" "}}because it misses data we need.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it{{" "}}becauseit misses required aspects.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it{{" "}}becauseit is not sufficient quality.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it{{" "}}because its conditions of use do not allow us to use it.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
            We considered reusing this non-reference data, but decided not to reuse it{{" "}}because: "{{nrefDataUseNoOtherReasonReply}}".
          {%- elif nrefDataUseNoReply -%}
            We considered reusing this non-reference data, but decided not to reuse it.
          {%- else -%}
            We considered reusing this non-reference data.
          {%- endif -%}
          </p>
"""

    nref_data_conditions_markdown_original = """
          {%- if nrefDataConditionsReply %}
            <p>This data are{{+" "}}
            {%- if nrefDataConditionsReply == uuids.nrefDataConditionsCC0AUuid -%}
              freely available for any use.
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsCCBYAUuid -%}
              freely available with obligation to quote the source.
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsOtherAUuid  -%}
              {%- set nrefDataConditionsOther = [nrefDataConditions, uuids.nrefDataConditionsOtherAUuid, uuids.nrefDataConditionsOtherQUuid]|reply_path -%}
              {%- set nrefDataConditionsOtherReply = repliesMap[nrefDataConditionsOther]|reply_str_value -%}
              {%- if nrefDataConditionsOtherReply -%}
                available with{{" "}}
                  {%- if nrefDataConditionsOtherReply -%}
                   following restrictions: {{nrefDataConditionsOtherReply|markdown}}
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
              {%- endif -%}
            {%- endif -%}
            </p>
          {%- endif -%}
"""
    nref_data_conditions_markdown_replacement = """
          {%- if nrefDataConditionsReply %}
            {%- if nrefDataConditionsReply == uuids.nrefDataConditionsCC0AUuid -%}
              <p>This data are{{+" "}}freely available for any use.</p>
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsCCBYAUuid -%}
              <p>This data are{{+" "}}freely available with obligation to quote the source.</p>
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsOtherAUuid  -%}
              {%- set nrefDataConditionsOther = [nrefDataConditions, uuids.nrefDataConditionsOtherAUuid, uuids.nrefDataConditionsOtherQUuid]|reply_path -%}
              {%- set nrefDataConditionsOtherReply = repliesMap[nrefDataConditionsOther]|reply_str_value -%}
              {%- if nrefDataConditionsOtherReply -%}
                <p>This data are{{+" "}}available with following restrictions: {{nrefDataConditionsOtherReply|markdown}}</p>
              {%- else -%}
                <p>This data are{{+" "}}available with restrictions, that will be specified.</p>
              {%- endif -%}
            {%- endif -%}
          {%- endif -%}
"""

    nref_data_not_used_identification_markdown_original = """
          <p>We considered reusing this non-reference data 
          {%- if nrefDataWhere -%}
          {{+" "}}available via:{{" "}}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              <a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
            {%- else -%}
              {{ nrefDataWhere }}
            {%- endif -%}
          {%- endif -%}

          {# no usage reason #}
          {%- if nrefDataUseNoReply -%}
            , but decided not to reuse it
            {%- if nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
              {{" "}}because it misses data we need
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
              {{" "}}becauseit misses required aspects
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
              {{" "}}becauseit is not sufficient quality
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
              {{" "}}because its conditions of use do not allow us to use it
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
              {{" "}}because: {{nrefDataUseNoOtherReasonReply|markdown}}
            {%- else -%}
             .
            {%- endif -%}

          {%- else -%}
          .</p>
          {%- endif -%}
"""
    nref_data_not_used_identification_markdown_replacement = """
          <p>
          {# no usage reason #}
          {%- if nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it because it misses data we need.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it becauseit misses required aspects.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it becauseit is not sufficient quality.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it because its conditions of use do not allow us to use it.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it because: {{nrefDataUseNoOtherReasonReply|markdown}}
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) and nrefDataUseNoReply -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>, but decided not to reuse it.
          {%- elif nrefDataWhere and (nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://")) -%}
            We considered reusing this non-reference data available via:{{" "}}<a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it because it misses data we need.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it becauseit misses required aspects.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it becauseit is not sufficient quality.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it because its conditions of use do not allow us to use it.
          {%- elif nrefDataWhere and nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it because: {{nrefDataUseNoOtherReasonReply|markdown}}
          {%- elif nrefDataWhere and nrefDataUseNoReply -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}, but decided not to reuse it.
          {%- elif nrefDataWhere -%}
            We considered reusing this non-reference data available via:{{" "}}{{ nrefDataWhere }}.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it because it misses data we need.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it becauseit misses required aspects.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it becauseit is not sufficient quality.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
            We considered reusing this non-reference data, but decided not to reuse it because its conditions of use do not allow us to use it.
          {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
            We considered reusing this non-reference data, but decided not to reuse it because: {{nrefDataUseNoOtherReasonReply|markdown}}
          {%- elif nrefDataUseNoReply -%}
            We considered reusing this non-reference data, but decided not to reuse it.
          {%- else -%}
            We considered reusing this non-reference data.
          {%- endif -%}
          </p>
"""

    shared_workspace_original = """
    {%- if sharedWorkspaceReply == uuids.sharedWorkspaceYesAUuid and sharedWorkspaceReliablePreventLossReply -%}
     <p>During the project we will use shared working space to work with our data{{+" "}}
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
      {%- endif -%}
     </p>

    {%- endif -%}
"""
    shared_workspace_replacement = """
    {%- if sharedWorkspaceReply == uuids.sharedWorkspaceYesAUuid and sharedWorkspaceReliablePreventLossReply -%}
     <p>
      {%- if sharedWorkspaceReliablePreventLossReply == uuids.sharedReliablePreventLossSufficientAUuid  -%}
        During the project we will use shared working space to work with our data{{+" "}}that ensures the prevention of complete data loss.
      {%- elif sharedWorkspaceReliablePreventLossReply == uuids.sharedReliablePreventLossStoredAUuid -%}
        During the project we will use shared working space to work with our data{{+" "}}but we will store all essential data elsewhere.
      {%- endif -%}

      {%- set sharedWorkspaceReliableBackupQUuid = [sharedWorkspaceReliableAUuid, uuids.sharedReliableBackupQUuid]|reply_path -%}
      {%- set sharedWorkspaceReliableBackupReply = repliesMap[sharedWorkspaceReliableBackupQUuid]|reply_str_value  -%}
      {%- if sharedWorkspaceReliableBackupReply == uuids.sharedReliableBackupCopyAllSomewhereAUuid -%}
        {{+" "}}And all the data that are stores elsewhere is adequately backed up.
      {%- elif sharedWorkspaceReliableBackupReply == uuids.sharedReliableBackupCopyBackupsAUuid -%}
        {{+" "}}We make (automated) backups of all data stored outside of the working area.
      {%- endif -%}
     </p>

    {%- endif -%}
"""

    published_software_original = """
                            {%- for swItem in isPublishedSwItems -%}
                                {%- set swNameUuid = [isPublishedSWPath, swItem, uuids.publishedSpecSwUseWhatNameQUuid]|reply_path -%}
                                {%- set swNameReply = repliesMap[swNameUuid]|reply_str_value -%}
                                {%- set swPIDUuid = [isPublishedSWPath, swItem, uuids.publishedSpecSwUseWhatPIDQUuid]|reply_path -%}
                                {%- set swPIDReply = repliesMap[swPIDUuid]|reply_str_value -%}
                                <p><strong>{{ swNameReply if swNameReply else "(no name given)" }}</strong>
                                {%- if swPIDReply -%}
                                , available at {{swPIDReply|dot}}</p>
                                {%- else -%}
                                .
                                {%- endif -%}
                            {%- endfor -%}
"""
    published_software_replacement = """
                            {%- for swItem in isPublishedSwItems -%}
                                {%- set swNameUuid = [isPublishedSWPath, swItem, uuids.publishedSpecSwUseWhatNameQUuid]|reply_path -%}
                                {%- set swNameReply = repliesMap[swNameUuid]|reply_str_value -%}
                                {%- set swPIDUuid = [isPublishedSWPath, swItem, uuids.publishedSpecSwUseWhatPIDQUuid]|reply_path -%}
                                {%- set swPIDReply = repliesMap[swPIDUuid]|reply_str_value -%}
                                {%- if swNameReply -%}
                                  {%- set swDisplayName = swNameReply -%}
                                {%- else -%}
                                  {%- set swDisplayName = "(no name given)" -%}
                                {%- endif -%}
                                {%- if swPIDReply -%}
                                <p><strong>{{ swDisplayName }}</strong>, available at {{swPIDReply|dot}}</p>
                                {%- else -%}
                                <p><strong>{{ swDisplayName }}</strong>.</p>
                                {%- endif -%}
                            {%- endfor -%}
"""

    format_volume_original = """
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
"""
    format_volume_replacement = """
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
                {% set formatsVolumeApproxGB = (formatsVolumeFiles|int * formatsVolumeFileGB|float)|round(2) %}
                We expect to have {{ formatsVolumeFiles }} files of average size {{ formatsVolumeFileGB }} GB (i.e. approximately {{ formatsVolumeApproxGB }} GB in total).
              {%- endif -%}
            {%- endif -%}
"""

    nonstandard_format_other_reason_original = """
                We are not using a standardized format
                {%- if formatsWhyNSAnotherReason -%}
                  , because: {{ formatsWhyNSAnotherReason|capitalize }}
                {%- endif -%}
                .
"""
    nonstandard_format_other_reason_replacement = """
                {%- if formatsWhyNSAnotherReason -%}
                  We are not using a standardized format, because: {{ formatsWhyNSAnotherReason|capitalize }}.
                {%- else -%}
                  We are not using a standardized format.
                {%- endif -%}
"""

    published_license_heading_original = """
                        {%- if licensesItems|length > 0 %}
                            The distribution will be available under the following {{ "licenses" if licensesItems|length > 1 else "license" }}:
                            <ul>
"""
    published_license_heading_replacement = """
                        {%- if licensesItems|length > 0 %}
                            {%- if licensesItems|length > 1 -%}
                              The distribution will be available under the following licenses:
                            {%- else -%}
                              The distribution will be available under the following license:
                            {%- endif -%}
                            <ul>
"""

    published_data_fixed_period_original = """
            {%- elif publishedDataHowLongAUuid == uuids.publishedDataHowLongFixedAUuid -%}
              {%- set publishedDataHowLongFixedPath = [publishedDataHowLongPath, uuids.publishedDataHowLongFixedAUuid, uuids.publishedDataHowLongFixedQUuid]|reply_path -%}
              {%- set publishedDataHowLongFixed = repliesMap[publishedDataHowLongFixedPath]|reply_str_value -%}
              <p>This data set will be kept available for a fixed period (prepaid){{ " of: " ~ publishedDataHowLongFixed|dot if publishedDataHowLongFixed else "." }}</p>
            {%- endif -%}
"""
    published_data_fixed_period_replacement = """
            {%- elif publishedDataHowLongAUuid == uuids.publishedDataHowLongFixedAUuid -%}
              {%- set publishedDataHowLongFixedPath = [publishedDataHowLongPath, uuids.publishedDataHowLongFixedAUuid, uuids.publishedDataHowLongFixedQUuid]|reply_path -%}
              {%- set publishedDataHowLongFixed = repliesMap[publishedDataHowLongFixedPath]|reply_str_value -%}
              {%- if publishedDataHowLongFixed -%}
                <p>This data set will be kept available for a fixed period (prepaid) of: {{ publishedDataHowLongFixed|dot }}</p>
              {%- else -%}
                <p>This data set will be kept available for a fixed period (prepaid).</p>
              {%- endif -%}
            {%- endif -%}
"""

    return apply_reversible_replacement_groups(
        source_text,
        (
            ReversibleReplacementGroup(
                "balanced_science_europe_sentence_blocks",
                (
                    (ref_data_conditions_original, ref_data_conditions_replacement),
                    (
                        ref_data_conditions_markdown_original,
                        ref_data_conditions_markdown_replacement,
                    ),
                    (nref_data_conditions_original, nref_data_conditions_replacement),
                    (
                        measured_external_ownership_original,
                        measured_external_ownership_replacement,
                    ),
                    (
                        nref_personal_legal_basis_original,
                        nref_personal_legal_basis_replacement,
                    ),
                    (computer_readable_original, computer_readable_replacement),
                    (
                        computer_readable_standardised_list_original,
                        computer_readable_standardised_list_replacement,
                    ),
                    (
                        computer_readable_standardized_list_original,
                        computer_readable_standardized_list_replacement,
                    ),
                    (
                        ref_data_used_identification_original,
                        ref_data_used_identification_replacement,
                    ),
                    (
                        ref_data_used_identification_markdown_original,
                        ref_data_used_identification_markdown_replacement,
                    ),
                    (
                        nref_data_used_identification_original,
                        nref_data_used_identification_replacement,
                    ),
                    (
                        nref_data_used_identification_markdown_original,
                        nref_data_used_identification_markdown_replacement,
                    ),
                    (
                        nref_data_used_identification_rnef_link_original,
                        nref_data_used_identification_rnef_link_replacement,
                    ),
                    (nref_data_complete_original, nref_data_complete_replacement),
                    (nref_data_fixed_original, nref_data_fixed_replacement),
                    (
                        ref_data_not_used_identification_original,
                        ref_data_not_used_identification_replacement,
                    ),
                    (
                        ref_data_not_used_identification_markdown_original,
                        ref_data_not_used_identification_markdown_replacement,
                    ),
                    (
                        nref_data_conditions_markdown_original,
                        nref_data_conditions_markdown_replacement,
                    ),
                    (
                        nref_data_not_used_identification_original,
                        nref_data_not_used_identification_replacement,
                    ),
                    (
                        nref_data_not_used_identification_markdown_original,
                        nref_data_not_used_identification_markdown_replacement,
                    ),
                    (shared_workspace_original, shared_workspace_replacement),
                    (published_software_original, published_software_replacement),
                    (format_volume_original, format_volume_replacement),
                    (
                        nonstandard_format_other_reason_original,
                        nonstandard_format_other_reason_replacement,
                    ),
                    (published_license_heading_original, published_license_heading_replacement),
                    (published_data_fixed_period_original, published_data_fixed_period_replacement),
                ),
            ),
        ),
    )


def rewrite_science_europe_unbalanced_html_fragments(source_text: str) -> str:
    """Patch upstream Science Europe sentence fragments that generic HTML cannot see.

    A few upstream fragments live inside large, unbalanced list-item wrappers, so
    the generic paragraph rewriter cannot safely discover their `<p>` boundaries.
    These replacements are still reversible: compacting restores the exact
    upstream text stored in the marker payload.
    """

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
        The data cannot become completely open because 
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
                
                {%- if measuredDataReuseOtherFieldHowReply -%}
                
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

    replacements = (
        (personal_data_legal_basis_original, personal_data_legal_basis_replacement),
        (copyright_open_reasons_original, copyright_open_reasons_replacement),
        (measured_reuse_other_field_original, measured_reuse_other_field_replacement),
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

    return apply_reversible_replacement_groups(
        source_text,
        (
            ReversibleReplacementGroup(
                "unbalanced_science_europe_html_fragments",
                replacements,
            ),
        ),
    )
