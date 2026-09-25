import java.nio.file.Paths;
public final class ArtifactOriginCheck {
public static void main(String[] args) throws Exception {
java.net.URI uri = cn.qizhang.guard.core.GuardService.class.getProtectionDomain().getCodeSource().getLocation().toURI();
if (!Paths.get(uri).toRealPath().equals(Paths.get(args[0]).toRealPath())) throw new AssertionError("Production class came from a different location");
System.out.println("PASS: production GuardService loaded from the explicitly pinned artifact");
}}
