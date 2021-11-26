[#--
SPDX-FileCopyrightText: 2020 HERE Europe B.V.
SPDX-FileCopyrightText: 2020-2021 Bosch.IO GmbH
SPDX-FileCopyrightText: 2021 Agora Voting SL

SPDX-License-Identifier: AGPL-3.0-only
--]

[#--
The AsciiDoc file generated by this template consists of the following sections:

* The licenses and associated copyrights for all projects merged into a single list.
* The archived license files, licenses and associated copyrights for dependencies listed by package.
* An Appendix of license texts of all above licenses

Excluded projects and packages are ignored.
--]

[#assign ModelExtensions = statics['org.ossreviewtoolkit.model.utils.ExtensionsKt']]

[#-- Add the licenses of the projects. --]
:title-page:
:sectnums:
:toc: preamble

[#assign errorTitle = "DISCLAIMER! THERE ARE UNRESOLVED ISSUES OR UNRESOLVED RULE VIOLATIONS.
    THIS DOCUMENT SHOULD NOT BE DISTRIBUTED UNTIL THESE PROBLEMS ARE RESOLVED."?replace("\n", " ")]

[#--
The alert role needs to be defined in the pdf-theme file, where the color can be customized.
If not present, the text is displayed normally.
--]
= [#if helper.hasUnresolvedIssues() || helper.hasUnresolvedRuleViolations()][.alert]#${errorTitle}#[#else] Disclosure Document[/#if]

:author-name: OSS Review Toolkit
[#assign now = .now]
:revdate: ${now?date?iso_local}
:revnumber: 1.0.0

== Issue Summary

[#-- List all issues and their status --]
[#if tabularScanRecord.issueSummary.rows?size > 0]

[#assign
issueErrors = tabularScanRecord
    .issueSummary
    .errorCount
]

[#assign
issueWarns = tabularScanRecord
    .issueSummary
    .warningCount
]

[#assign
issueHint = tabularScanRecord
    .issueSummary
    .hintCount
]
${issueErrors} errors, ${issueWarns} warnings, ${issueHint} hints to resolve
[#else]
0 errors, 0 warnings, 0 hints to resolve[/#if]

== Projects Licenses
[#if projects?has_content]
[#--Merge the licenses and copyrights of all projects into a single list. The default LicenseView.ALL is used because--]
[#--projects cannot have a concluded license (compare with the handling of packages below). --]

[#list projects as project]

=== ${project.id.name}

[#assign mergedLicenses = helper.mergeLicenses([project])]


[#list mergedLicenses as resolvedLicense]

* License: <<${resolvedLicense.license}, ${resolvedLicense.license}>>

[#assign copyrights = resolvedLicense.getCopyrights(true)]
[#list copyrights as copyright]
** +${copyright}+
[/#list]
[/#list]
[/#list]
[/#if]

[#-- List all rule violations and their status --]
== Rule Violation Summary

[#assign
ruleViolationErrors = tabularScanRecord
    .ruleViolations
    ?filter( it -> !it.isResolved() && it.violation.severity.name() == "ERROR" )
    ?size
]

[#assign
ruleViolationWarns = tabularScanRecord
    .ruleViolations
    ?filter( it -> !it.isResolved() && it.violation.severity.name() == "WARNING" )
    ?size
]

[#assign
ruleViolationHint = tabularScanRecord
    .ruleViolations
    ?filter( it -> !it.isResolved() && it.violation.severity.name() == "HINT" )
    ?size
]
${ruleViolationErrors} errors, ${ruleViolationWarns} warnings, ${ruleViolationHint} hints to resolve

[#if tabularScanRecord.ruleViolations?size == 0]
No rule violations found.
[#else]

[#list tabularScanRecord.ruleViolations as ruleViolation]

|====
| **Rule:** | ${ruleViolation.violation.rule}
| **Severity:** | [#if ruleViolation.isResolved()]**Resolved**[#else]**${ruleViolation.violation.severity.name()}**[/#if]
| **Package:** | ${ruleViolation.violation.pkg.toCoordinates()} 
| **License:** | [#if ruleViolation.violation.license?has_content]${ruleViolation.violation.licenseSource}: ${ruleViolation.violation.license}[#else]-[/#if]
| **Message:** | ${ruleViolation.violation.message}
[#if ruleViolation.isResolved()]
| **Resolution:** | ${ruleViolation.resolutionDescription}
[#else]
| **How to fix:** | ${ruleViolation.violation.howToFix}
[/#if]
|====
[/#list]

[/#if]

[#-- Add the licenses of all dependencies. --]
== Dependencies

[#if packages?has_content]
This software depends on external packages and source code.
The applicable license information is listed below:
[/#if]

[#list packages as package]
[#if !package.excluded]

**Dependency: ${package.id.name}**

[#if package.description?has_content]
Description: ${package.description}
[/#if]

Package URL: _${ModelExtensions.toPurl(package.id)}_

[#-- List the content of archived license files and associated copyrights. --]
[#list package.licenseFiles.files as licenseFile]

License File: <<${ModelExtensions.toPurl(package.id)} ${licenseFile.path}, ${licenseFile.path}>>

[#assign copyrights = licenseFile.getCopyrights()]
[#list copyrights as copyright]
** +${copyright}+
[/#list]

[/#list]
[#--
Filter the licenses of the package using LicenseView.CONCLUDED_OR_DECLARED_AND_DETECTED. This is the default view which
ignores declared and detected licenses if a license conclusion for the package was made. If copyrights were detected
for a concluded license those statements are kept.
--]
[#assign
resolvedLicenses =
    LicenseView.CONCLUDED_OR_DECLARED_AND_DETECTED
      .filter(
          package.licensesNotInLicenseFiles(
            LicenseView.CONCLUDED_OR_DECLARED_AND_DETECTED
                .filter(package.license, package.licenseChoices).licenses
          )
      )
]
[#if resolvedLicenses?has_content]

The following licenses and copyrights were found in the source code of this package:
[/#if]

[#list resolvedLicenses as resolvedLicense]

[#-- In case of a NOASSERTION license, there is no license text; so do not add a link. --]
[#if helper.isLicensePresent(resolvedLicense)]
* License: <<${resolvedLicense.license}, ${resolvedLicense.license}>>
[#else]
* License: ${resolvedLicense.license}
[/#if]

[#assign copyrights = resolvedLicense.getCopyrights(true)]
[#list copyrights as copyright]
** +${copyright}+
[/#list]

[/#list]
[/#if]
[/#list]

[#assign
packagesWithLicenseFiles = 
    packages?filter(
        it -> !it.excluded && it.licenseFiles.files?size > 0
    )
]
[#if packagesWithLicenseFiles?has_content]

== License Files for Packages

[#list packagesWithLicenseFiles as package]
[#if !package.excluded]

*Dependency*

Package URL: _${ModelExtensions.toPurl(package.id)}_

[#list package.licenseFiles.files as licenseFile]
=== ${ModelExtensions.toPurl(package.id)} ${licenseFile.path}

++++
[#assign copyrights = licenseFile.getCopyrights()]
[#if copyrights?has_content]
[#list copyrights as copyright]
${copyright}
[#else]
No copyright
[/#list]
[/#if]

${licenseFile.readFile()}
++++
<<<
[#else]
No license file
[/#list]
[/#if]
[#else]
No package
[/#list]

[/#if]


[#--
Append the text of all licenses that have been listed in the above lists for licenses and coppyrights
--]
[appendix]
== License Texts

[#assign mergedLicenses = helper.mergeLicenses(projects + packages, LicenseView.CONCLUDED_OR_DECLARED_AND_DETECTED, true)]
[#list mergedLicenses as resolvedLicense]
=== ${resolvedLicense.license}

++++
[#assign licenseText = licenseTextProvider.getLicenseText(resolvedLicense.license.simpleLicense())!""]
[#if licenseText?has_content]

[#assign copyrights = resolvedLicense.getCopyrights(true)]
[#list copyrights as copyright]
${copyright}
[/#list]

${licenseText}

[#assign exceptionText = licenseTextProvider.getLicenseText(resolvedLicense.license.exception()!"")!""]
[#if exceptionText?has_content]

${exceptionText}

[/#if]
[/#if]
[/#list]
