import java.nio.file.Paths;
public final class ArtifactOriginCheck {
 public static void main(String[] args) throws Exception {
  java.net.URI actual = cn.qizhang.guard.core.GuardService.class.getProtectionDomain().getCodeSource().getLocation().toURI();
  if (!Paths.get(actual).toRealPath().equals(Paths.get(args[0]).toRealPath())) throw new AssertionError("Wrong core source");
  System.out.println("PASS: exact packaged core origin");
 }}
