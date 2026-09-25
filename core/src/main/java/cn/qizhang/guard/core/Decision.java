package cn.qizhang.guard.core;

/** A policy result; ALERT results are allowed, with an actionable code. */
public final class Decision {
    private final boolean allowed;
    private final String code;
    private final String message;
    private Decision(boolean allowed, String code, String message) {
        this.allowed = allowed; this.code = code; this.message = message;
    }
    public static Decision allow() { return new Decision(true, "OK", "Allowed"); }
    public static Decision alert(String code, String message) { return new Decision(true, code, message); }
    public static Decision deny(String code, String message) { return new Decision(false, code, message); }
    public boolean allowed() { return allowed; }
    public String code() { return code; }
    public String message() { return message; }
    @Override public String toString() { return code + ": " + message; }
}
