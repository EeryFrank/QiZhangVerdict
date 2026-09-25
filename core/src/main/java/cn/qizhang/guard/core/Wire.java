package cn.qizhang.guard.core;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/** Versioned, strict UTF-8, length-prefixed protocol. No deserialization or client-held secrets. */
public final class Wire {
    public static final String CHANNEL = "qzguard:main";
    public static final int MAX_PAYLOAD = 30000;
    public static final int MAX_MODS = 1024;
    public static final int MAX_PACKS = 128;
    public static final int MAX_VM_SIGNALS = 32;
    private static final int MAGIC = 0x515A4731;
    private static final String DEFAULT_SCOPE = "0000000000000000000000000000000000000000000000000000000000000000";
    private Wire() { }
    public static byte[] encodeChallenge(String nonce) {
        return encodeChallenge(nonce, DEFAULT_SCOPE);
    }
    public static byte[] encodeChallenge(String nonce, String serverScope) {
        try {
            validateNonce(nonce); validateNonce(serverScope);
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            DataOutputStream out = new DataOutputStream(bytes);
            header(out, 1); writeString(out, nonce, 64); writeString(out, serverScope, 64);
            return finish(bytes);
        } catch (IOException ex) { throw new IllegalArgumentException(ex.getMessage(), ex); }
    }
    public static String decodeChallenge(byte[] payload) throws IOException {
        return decodeChallengeFields(payload)[0];
    }
    public static String decodeServerScope(byte[] payload) throws IOException {
        return decodeChallengeFields(payload)[1];
    }
    private static String[] decodeChallengeFields(byte[] payload) throws IOException {
        DataInputStream in = input(payload, 1);
        String nonce = readString(in, 64), scope = readString(in, 64);
        validateNonce(nonce); validateNonce(scope); end(in); return new String[]{nonce, scope};
    }
    public static byte[] encodeReport(String nonce, ClientReport report) {
        try {
            if (report == null) throw new IOException("Missing report");
            validateNonce(nonce);
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            DataOutputStream out = new DataOutputStream(bytes);
            header(out, 2); writeString(out, nonce, 64); out.writeByte(report.complete() ? 1 : 0);
            writeList(out, report.modIds(), MAX_MODS, 128);
            writeList(out, report.resourcePacks(), MAX_PACKS, 256);
            writeList(out, report.vmSignals(), MAX_VM_SIGNALS, 64);
            if (report.deviceId().isEmpty()) out.writeShort(0); else writeString(out, report.deviceId(), 64);
            return finish(bytes);
        } catch (IOException ex) { throw new IllegalArgumentException(ex.getMessage(), ex); }
    }
    public static ReportEnvelope decodeReport(byte[] payload) throws IOException {
        DataInputStream in = input(payload, 2);
        String nonce = readString(in, 64); validateNonce(nonce);
        int complete = in.readUnsignedByte();
        if (complete > 1) throw new IOException("Invalid completeness flag");
        List<String> mods = readList(in, MAX_MODS, 128), packs = readList(in, MAX_PACKS, 256), signals = readList(in, MAX_VM_SIGNALS, 64);
        int deviceLength = in.readUnsignedShort();
        if (deviceLength != 0 && deviceLength != 64) throw new IOException("Invalid device digest length");
        byte[] deviceBytes = new byte[deviceLength]; in.readFully(deviceBytes);
        String device = new String(deviceBytes, StandardCharsets.US_ASCII);
        if (!device.isEmpty() && !device.matches("[0-9a-f]{64}")) throw new IOException("Invalid device digest");
        ClientReport report = new ClientReport(mods, packs, signals, complete == 1, device);
        end(in); return new ReportEnvelope(nonce, report);
    }
    private static void validateNonce(String nonce) throws IOException {
        if (nonce == null || !nonce.matches("[0-9a-f]{64}")) throw new IOException("Invalid nonce");
    }
    private static void header(DataOutputStream out, int type) throws IOException {
        out.writeInt(MAGIC); out.writeByte(2); out.writeByte(type);
    }
    private static DataInputStream input(byte[] bytes, int type) throws IOException {
        if (bytes == null || bytes.length > MAX_PAYLOAD || bytes.length < 6) throw new IOException("Invalid payload size");
        DataInputStream in = new DataInputStream(new ByteArrayInputStream(bytes));
        if (in.readInt() != MAGIC || in.readUnsignedByte() != 2 || in.readUnsignedByte() != type)
            throw new IOException("Unsupported protocol or message type");
        return in;
    }
    private static void writeList(DataOutputStream out, List<String> values, int max, int width) throws IOException {
        if (values == null || values.size() > max) throw new IOException("Too many list entries");
        out.writeShort(values.size());
        for (String value : values) writeString(out, value, width);
    }
    private static List<String> readList(DataInputStream in, int max, int width) throws IOException {
        int count = in.readUnsignedShort();
        if (count > max) throw new IOException("Too many list entries");
        ArrayList<String> values = new ArrayList<String>(count);
        for (int i = 0; i < count; i++) values.add(readString(in, width));
        return values;
    }
    private static void writeString(DataOutputStream out, String value, int max) throws IOException {
        validateText(value);
        byte[] bytes;
        try {
            ByteBuffer buffer = StandardCharsets.UTF_8.newEncoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).encode(java.nio.CharBuffer.wrap(value));
            bytes = new byte[buffer.remaining()]; buffer.get(bytes);
        } catch (CharacterCodingException ex) { throw new IOException("Invalid UTF-8 text", ex); }
        if (bytes.length == 0 || bytes.length > max) throw new IOException("Invalid text size");
        out.writeShort(bytes.length); out.write(bytes);
    }
    private static String readString(DataInputStream in, int max) throws IOException {
        int length = in.readUnsignedShort();
        if (length == 0 || length > max || length > in.available()) throw new IOException("Invalid text size");
        byte[] bytes = new byte[length]; in.readFully(bytes);
        String value;
        try {
            value = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
        } catch (CharacterCodingException ex) { throw new IOException("Invalid UTF-8 text", ex); }
        validateText(value); return value;
    }
    private static void validateText(String value) throws IOException {
        if (value == null) throw new IOException("Missing text");
        for (int i = 0; i < value.length(); i++) if (Character.isISOControl(value.charAt(i))) throw new IOException("Control character in text");
    }
    private static void end(DataInputStream in) throws IOException {
        if (in.available() != 0) throw new IOException("Trailing bytes");
    }
    private static byte[] finish(ByteArrayOutputStream bytes) throws IOException {
        if (bytes.size() > MAX_PAYLOAD) throw new IOException("Report exceeds maximum payload");
        return bytes.toByteArray();
    }
}
