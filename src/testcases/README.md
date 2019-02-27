# SAS test cases

## Organization

The current test cases are based on the [WinnForum test specification](https://workspace.winnforum.org/higherlogic/ws/public/download/5637/WINNF-TS-0061-V1.1.0%20-%20WG4%20SAS%20Test%20and%20Certification%20Spec.pdf) v1.1 (Jan 2018)

## Security Test Cases

The following test cases expect handshake failures due to certificate revocation
(though they don't validate the reason for the failure):

- SCS_11
- SCS_16
- SDS_11
- SDS_16
- SSS_11
- SSS_16

They may be run against fake_sas by injecting the CRL files directly:

    $ python fake_sas.py --crl_index certs/crl/crl_index_sxs11.txt
    $ python fake_sas.py --crl_index certs/crl/crl_index_sxs16.txt

As WinnF WG.2 and ITS approved to use CRL as the initial certificate blacklisting solution before OCSP is available, 
came up with following agreements

<b>Agreements:</b>
1. Deploy a CRL server (a.k.a The certificate revocation list distribution point CDP) in the ITS designated VM environment 
to serve as a FCC certification dedicated CRL server.

2. Certificates, sub-CAs to be blacklisted for all the test cases (e.g. SCS.11 and SCS.16 etc.) will be created and 
per-loaded into the CRL server appropriately. There is NO need for the test harness codes to blacklist a certificate 
or sub-CA on-demand. During the test, the test codes will directly use the certificate or sub-CA that are already 
in the CRL.

3. SAS UUT is assumed to pull the CRL periodically as if in normal operation. There is only a coordination need, 
that is to make sure SAS UUT has the latest CRL information before running the related test cases.

If a SAS UUT is used for testing the CRL test cases then the steps to manually download the CRL file using wget and 
concatenating it with the CA chain would not be needed as the <b>simple CRL server</b> is used to mimic an actual 
CRL server and the CDP URL field of the certificates is updated with the URL of the <b>simple CRL server</b>. 
As fake_sas updates are on a best effort basis and the intention is to keep it simple, the automatic retrieval of 
CRL file is not implemented in fake_sas.

To obtain the CRL file, the <b>simple CRL server</b> in <b>master</b> branch needs to be 
executed and a CRL chain can be retrieved from this server.

The details of using the <b>simple CRL server</b> is documented under <b>harness/CRLServer-README.md file</b>. 
The simple CRL server is also enhanced with simpler menu option and ability to blacklist intermediate CAs.
