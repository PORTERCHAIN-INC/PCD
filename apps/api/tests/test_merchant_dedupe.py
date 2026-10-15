from porterchain_api.merchant_engine import dedupe as d

KAY = d.Candidate(id="8a17", company_name="KAYLULU", emails=["tracylu.business@gmail.com"])


def test_kaylulu_install_suggests_existing():
    m = d.resolve(d.Probe(company_name="Kaylulu", email="hello@kaylulu.ca", shop_domain="8hpwwc-rx.myshopify.com"), [KAY])
    assert m.decision in ("suggest", "link") and m.merchant_id == "8a17"


def test_admin_issued_install_links():
    c = d.Candidate(id="8a17", company_name="KAYLULU", pending_install_shops=["8hpwwc-rx.myshopify.com"])
    m = d.resolve(d.Probe(company_name="Whatever", email="x@y.ca", shop_domain="8hpwwc-rx.myshopify.com"), [c])
    assert m.decision == "link" and m.reasons == ["admin_issued_install_url"]


def test_company_domain_plus_name_links():
    c = d.Candidate(id="1", company_name="Acme Ltd.", emails=["ops@acme.ca"])
    assert d.resolve(d.Probe(company_name="ACME Inc", email="sales@acme.ca"), [c]).decision == "link"


def test_free_mail_never_matches_on_domain():
    c = d.Candidate(id="1", company_name="Foo", emails=["a@gmail.com"])
    assert d.resolve(d.Probe(company_name="Bar", email="b@gmail.com"), [c]).decision == "new"


def test_business_number_links():
    c = d.Candidate(id="1", company_name="X", hst_number="123456789 RT0001")
    assert d.resolve(d.Probe(company_name="Y", business_number="123456789"), [c]).decision == "link"


def test_normalizers():
    assert d.norm_phone("(905) 555-1212") == "+19055551212"
    assert d.norm_name("Kaylulu Inc.") == "kaylulu"
    assert d.norm_postal("l6h 1a1") == "L6H1A1"
    assert d.web_domain("https://www.kaylulu.ca/shop") == "kaylulu.ca"


def test_unrelated_is_new():
    assert d.resolve(d.Probe(company_name="Maple Wholesale", email="a@maple.ca"), [KAY]).decision == "new"
