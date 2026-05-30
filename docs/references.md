# References

Bibliography for "From Multivendor Diagnosis to Closed-Loop Remediation: An Agent Harness for Cloud RAN
Day-2." nGRG Workshop, Seattle, 4th [THU] JUN 2026. Citations follow AMA format. Numbered references
correspond to the architecture components and routing-rule chain described in the abstract and in
talk/architecture.mmd.

Companion documents:
- talk/abstract.md, the canonical submission
- talk/oda_mapping.md, the 15-element ODA Canvas reference mapping
- harness/conformance.md, the file-by-file conformance index
- harness/references/, per-contract upstream pointers with commit SHA pins

---

## A. O-RAN Alliance specifications (architecture and O2 interface)

1. O-RAN Alliance. O-RAN Architecture Description. Working Group 1 specification. O-RAN Alliance e.V.
   https://www.o-ran.org/specifications. Accessed 14th [WED] MAY 2026.

2. O-RAN Alliance. O-RAN O2 General Aspects and Principles. Working Group 6 specification
   (O-RAN.WG6.O2-GAnP). O-RAN Alliance e.V. https://www.o-ran.org/specifications. Accessed 14th [WED] MAY 2026.

3. O-RAN Alliance. O-RAN O2 IMS Interface Specification (Infrastructure Management Services). Working
   Group 6 specification (O-RAN.WG6.O2IMS-Interface). O-RAN Alliance e.V. https://www.o-ran.org/specifications.
   Accessed 14th [WED] MAY 2026.

4. O-RAN Alliance. O-RAN O2 DMS Interface Specification (Deployment Management Services). Working Group
   6 specification (O-RAN.WG6.O2DMS-Interface). O-RAN Alliance e.V. https://www.o-ran.org/specifications. Accessed
   14th [WED] MAY 2026.

5. O-RAN Software Community. O2 IMS Compliance Test Suite. Linux Foundation, O-RAN SC.
   https://github.com/o-ran-sc/it-test. Accessed 14th [WED] MAY 2026.

## B. O-Cloud, cluster lifecycle, and bare-metal management

6. OpenShift Kubernetes-Native Infrastructure project. oran-o2ims: O-Cloud Manager. GitHub. Red Hat.
   https://github.com/openshift-kni/oran-o2ims. Accessed 14th [WED] MAY 2026.

7. Metal3 project. Metal3: Bare metal host provisioning for Kubernetes. https://metal3.io. Accessed
   14th [WED] MAY 2026.

8. Metal3 project. Baremetal Operator: BareMetalHost, HostFirmwareSettings, HostFirmwareComponents
   Custom Resource Definitions. GitHub. https://github.com/metal3-io/baremetal-operator. Accessed
   14th [WED] MAY 2026.

9. OpenShift project. Machine Config Operator: declarative configuration of Red Hat Enterprise Linux
   CoreOS. GitHub. https://github.com/openshift/machine-config-operator. Accessed 14th [WED] MAY 2026.

10. Kubernetes Special Interest Groups. Kernel Module Management Operator (KMM). GitHub.
    https://github.com/kubernetes-sigs/kernel-module-management. Accessed 14th [WED] MAY 2026.

11. Red Hat. Red Hat Advanced Cluster Management for Kubernetes (RHACM) documentation. Red Hat Customer
    Portal. https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes.
    Accessed 14th [WED] MAY 2026.

12. Red Hat. Red Hat OpenShift Container Platform documentation: managing machine configurations.
    Red Hat Customer Portal. https://docs.redhat.com/en/documentation/openshift_container_platform.
    Accessed 14th [WED] MAY 2026.

## C. Agentic substrate: protocol and frameworks

13. Anthropic. Model Context Protocol Specification. https://modelcontextprotocol.io. Accessed 14th
    [WED] MAY 2026.

14. Anthropic. Model Context Protocol Python SDK. GitHub.
    https://github.com/modelcontextprotocol/python-sdk. Accessed 14th [WED] MAY 2026.

15. Lowin J. FastMCP: a pythonic framework for building Model Context Protocol servers and clients.
    GitHub. https://github.com/jlowin/fastmcp. Accessed 14th [WED] MAY 2026.

16. LangChain AI. LangGraph: building stateful, multi-actor applications with LLMs.
    https://langchain-ai.github.io/langgraph. Accessed 14th [WED] MAY 2026.

17. BerriAI. LiteLLM: unified interface to call 100+ LLM APIs using the OpenAI input/output format.
    GitHub. https://github.com/BerriAI/litellm. Accessed 14th [WED] MAY 2026.

## D. TM Forum standards

18. TM Forum. TMF688 Event Management API User Guide and REST Specification.
    https://www.tmforum.org/oda/open-apis/table/tmf688. Accessed 14th [WED] MAY 2026.

19. TM Forum. TMF921 Intent Management API User Guide and REST Specification.
    https://www.tmforum.org/oda/open-apis/table/tmf921. Accessed 14th [WED] MAY 2026.

20. TM Forum. TMF634 Resource Inventory Management API Specification.
    https://www.tmforum.org/oda/open-apis/table/tmf634. Accessed 14th [WED] MAY 2026.

21. TM Forum. TMF642 Alarm Management API Specification.
    https://www.tmforum.org/oda/open-apis/table/tmf642. Accessed 14th [WED] MAY 2026.

22. TM Forum. GB922 Information Framework (SID) Concepts and Principles. https://www.tmforum.org.
    Accessed 14th [WED] MAY 2026.

23. TM Forum. IG1228 AIOps and Intelligence Management Domain Implementation Guide.
    https://www.tmforum.org. Accessed 14th [WED] MAY 2026.

24. TM Forum. IG1190 Open Digital Architecture Functional Architecture. https://www.tmforum.org.
    Accessed 14th [WED] MAY 2026.

25. TM Forum. IG1253 / IG1253D Intent Manager Implementation Guide. https://www.tmforum.org. Accessed
    14th [WED] MAY 2026.

## E. Time synchronization, PTP host stack, and PTP event publishing

26. Institute of Electrical and Electronics Engineers. IEEE Std 1588-2019: IEEE Standard for a
    Precision Clock Synchronization Protocol for Networked Measurement and Control Systems. IEEE; 2019.
    https://standards.ieee.org/ieee/1588/6825/.

27. linuxptp project. ptp4l(8) manual page: PTP Boundary / Ordinary Clock daemon for Linux.
    https://linuxptp.sourceforge.net. Accessed 14th [WED] MAY 2026.

28. Red Hat. PTP Operator for OpenShift documentation.
    https://docs.redhat.com/en/documentation/openshift_container_platform. Accessed 14th [WED] MAY 2026.

29. Red Hat Cloud Native Events project. cloud-event-proxy: PTP notification publisher emitting
    O-RAN-compliant CloudEvents from linuxptp state changes. GitHub.
    https://github.com/redhat-cne/cloud-event-proxy. Accessed 14th [WED] MAY 2026.

30. Cloud Native Computing Foundation. CloudEvents version 1.0 specification: a vendor-neutral
    specification for describing event data. CNCF. https://cloudevents.io. Accessed 14th [WED] MAY 2026.

31. O-RAN Alliance. O-RAN Cloud Notifications specification. Working Group 6
    (O-RAN.WG6.Cloud-Notifications). O-RAN Alliance e.V. https://www.o-ran.org/specifications. Accessed 14th [WED]
    MAY 2026.

## F. RAN performance counters and 5G management

32. 3rd Generation Partnership Project. 3GPP TS 28.552: Management and orchestration; 5G performance
    measurements. 3GPP. https://www.3gpp.org/dynareport/28552.htm. Accessed 14th [WED] MAY 2026.

33. 3rd Generation Partnership Project. 3GPP TS 28.541: Management and orchestration; 5G Network
    Resource Model (NRM); Stage 2 and stage 3. 3GPP. https://www.3gpp.org/dynareport/28541.htm.
    Accessed 14th [WED] MAY 2026.

## G. Hardware reference (NIC driver and PHC behavior)

34. Intel Corporation. Intel Ethernet Controller E810 datasheet and driver release notes (ice driver).
    Intel Corporation.
    https://www.intel.com/content/www/us/en/products/details/ethernet/800-series-network-adapters.html.
    Accessed 14th [WED] MAY 2026.

## H. Prior multivendor demonstration (referenced for diagnostic substrate)

35. Kiani Mehr S, Korati Prasanna N, Kypuros D, Vazquez Cebrian M, Srikanthan S, Venkatesh P.
    Multivendor agentic AI solution for Cloud RAN troubleshooting. Ericsson Technology Blog. Published
    11th [MON] MAY 2026. https://www.ericsson.com/en/blog/2026/5/multivendor-agentic-ai-solution-for-cloud-ran.
    Accessed 14th [WED] MAY 2026.

## I. Adjacent cloud-native network automation projects (for landscape context)

36. Linux Foundation Networking. Nephio: Cloud-native network automation. https://nephio.org. Accessed
    14th [WED] MAY 2026.

37. Linux Foundation Networking. Open Network Automation Platform (ONAP). https://www.onap.org.
    Accessed 14th [WED] MAY 2026.

38. Linux Foundation Networking. Open Source MANO (OSM). https://osm.etsi.org. Accessed 14th [WED]
    MAY 2026.

## J. Upstream contracts referenced by harness/ stubs (commit-SHA-pinnable)

These references augment entries 5, 6, 9, 10, and 13. They are the specific snapshots that
harness/references/*.md files point to. Pinning commit SHAs is a follow-up step before 3rd [WED] JUN 2026
publication; placeholder notation below is intentional.

39. OpenShift KNI. oran-o2ims pinned snapshot. GitHub.
    https://github.com/openshift-kni/oran-o2ims/tree/913484da469255ebd9446d48ec65c8217bccf872. Pin target:
    O-Cloud Manager release used as the reference O2 IMS implementation.

40. Red Hat Cloud Native Events. cloud-event-proxy pinned snapshot. GitHub.
    https://github.com/redhat-cne/cloud-event-proxy/tree/3774ede771948d98290af1f3fdd1f5c006d5f2fa. Pin target:
    the CloudEvents schema versions the harness consumes.

41. OpenShift project. machine-config-operator MachineConfig CRD pinned snapshot. GitHub.
    https://github.com/openshift/machine-config-operator/tree/d72b715f8f9e0fad5d27a45420ea074ea2628207/
    manifests/machineconfiguration.crd.yaml. Pin target: the MachineConfig schema that scenarios
    A_fw_lldp_agent and A_prime_ice_driver conform to.

42. Kubernetes SIGs. kernel-module-management Module v1beta1 CRD pinned snapshot. GitHub.
    https://github.com/kubernetes-sigs/kernel-module-management/tree/b8e0265fe059dbb47a074a287f0d6b7d6d8c13ed/
    config/crd/bases/kmm.sigs.x-k8s.io_modules.yaml. Pin target: the Module shape that scenario
    A_prime_ice_driver conforms to.

43. Anthropic Model Context Protocol. MCP tool-schema specification pinned snapshot. GitHub.
    https://github.com/modelcontextprotocol/specification/tree/d069881d3e1dab5ae76b4bf20806d131d1aa84e5. Pin
    target: the JSON Schema shape that harness/mcp-tool-schemas/ conforms to.

---

## Notes on citation accuracy

a. O-RAN specifications are versioned and revised periodically. The references above cite the working
   group and document family rather than a fixed version number, since the authoritative version at the
   time of the workshop should be cited from https://www.o-ran.org/specifications.

b. TM Forum Open APIs and Implementation Guides are accessed through https://www.tmforum.org. Document
   numbers (TMFxxx, IGxxxx, GBxxx) are stable identifiers across revisions.

c. KMM (Kernel Module Management) was originally developed under the rh-ecosystem-edge organization
   before moving to kubernetes-sigs. Both repositories may be referenced depending on the OpenShift
   release.

d. Reference 35 is included as the proof point that an MCP-coordinated multivendor diagnostic substrate
   exists in published form. The talk's new contribution (the closed-loop remediation extension) builds
   architecturally on top of that substrate.

e. References 39 through 43 use placeholder commit-SHA notation. These will be pinned to actual SHAs
   before publication. Until then, the live URLs (refs 5, 6, 9, 10, 13, 29) remain authoritative.

f. References 44 through 47 cover standards named in the architecture diagram and tool descriptions
   (ITU-T G.8275.1 PTP telecom profile, O-RAN WG4 Open Fronthaul, DMTF Redfish, TMF902 AI Model
   Management). These are diagram context labels rather than primary conformance claims; the harness
   does not author content directly against these specs.

---

## K. Additional standards referenced in diagrams and tool descriptions

44. International Telecommunication Union, Telecommunication Standardization Sector. ITU-T G.8275.1:
    Precision time protocol telecom profile for phase / time synchronization with full timing support
    from the network. ITU-T; 2022. https://www.itu.int/rec/T-REC-G.8275.1. Accessed 14th [WED] MAY 2026.

45. O-RAN Alliance. O-RAN Open Fronthaul Interface Specifications. Working Group 4 (O-RAN.WG4).
    Covers Control, User, Synchronization, and Management planes carried over eCPRI. O-RAN Alliance e.V.
    https://www.o-ran.org/specifications. Accessed 14th [WED] MAY 2026.

46. Distributed Management Task Force. Redfish Specification. DMTF DSP0266. Standard for out-of-band
    management of servers and infrastructure. https://www.dmtf.org/standards/redfish. Accessed 14th
    [WED] MAY 2026.

47. TM Forum. TMF902 AI Model Management API. https://www.tmforum.org/oda/open-apis/table/tmf902.
    Accessed 14th [WED] MAY 2026.
