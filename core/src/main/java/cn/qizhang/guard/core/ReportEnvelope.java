package cn.qizhang.guard.core;

public final class ReportEnvelope {
    private final String nonce;
    private final ClientReport report;
    public ReportEnvelope(String nonce, ClientReport report) { this.nonce = nonce; this.report = report; }
    public String nonce() { return nonce; }
    public ClientReport report() { return report; }
}
