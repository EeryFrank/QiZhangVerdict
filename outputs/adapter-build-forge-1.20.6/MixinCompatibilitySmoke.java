// SPDX-License-Identifier: GPL-3.0-only
package cn.qizhang.guard.forge;

import com.google.gson.JsonParser;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.jar.JarFile;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.tree.ClassNode;
import org.spongepowered.asm.mixin.MixinEnvironment.CompatibilityLevel;
import org.spongepowered.asm.util.LanguageFeatures;
import org.spongepowered.asm.util.asm.ASM;

/** Checks the packaged resource and mixin class with Forge 50's real Mixin/ASM libraries. */
public final class MixinCompatibilitySmoke {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Expected the built mod JAR path");
        String mixinVersion = CompatibilityLevel.class.getPackage().getImplementationVersion();
        if (mixinVersion == null || !(mixinVersion.equals("0.8.5") || mixinVersion.startsWith("0.8.5+")))
            throw new AssertionError("Expected Forge 50's fixed Mixin 0.8.5, got " + mixinVersion);

        try (var jar = new JarFile(args[0])) {
            String configName = jar.getManifest().getMainAttributes().getValue("MixinConfigs");
            if (!"qizhangverdict.mixins.json".equals(configName))
                throw new AssertionError("Required Mixin manifest entry missing");
            var entry = jar.getJarEntry(configName);
            if (entry == null) throw new AssertionError("Packaged Mixin config missing");
            final com.google.gson.JsonObject config;
            try (var reader = new InputStreamReader(jar.getInputStream(entry), StandardCharsets.UTF_8)) {
                config = JsonParser.parseReader(reader).getAsJsonObject();
            }
            // This is the actual loader enum, not a locally maintained list of accepted strings.
            var level = CompatibilityLevel.valueOf(config.get("compatibilityLevel").getAsString());
            if (!config.get("required").getAsBoolean()
                    || config.getAsJsonObject("injectors").get("defaultRequire").getAsInt() != 1)
                throw new AssertionError("Command isolation Mixin must remain required with require=1");
            var mixins = config.getAsJsonArray("mixins");
            if (mixins.size() != 1 || !"CommandGate1206Mixin".equals(mixins.get(0).getAsString()))
                throw new AssertionError("Unexpected command isolation Mixin set");
            String classPath = config.get("package").getAsString().replace('.', '/')
                + "/" + mixins.get(0).getAsString() + ".class";
            var classEntry = jar.getJarEntry(classPath);
            if (classEntry == null) throw new AssertionError("Packaged command Mixin class missing");
            var node = new ClassNode();
            try (var input = jar.getInputStream(classEntry)) {
                new ClassReader(input).accept(node, 0);
            }
            int major = node.version & 0xFFFF;
            if (major != 65) throw new AssertionError("Minecraft 1.20.6 adapter must remain compiled for Java 21");
            if (major > ASM.getMaxSupportedClassVersionMajor())
                throw new AssertionError("Runtime ASM cannot read the compiled command Mixin");
            int features = LanguageFeatures.scan(node);
            if (!level.supports(features))
                throw new AssertionError("Compiled Mixin uses features unsupported by " + level);
            System.out.println("PASS: packaged required Mixin config parsed by Mixin " + mixinVersion
                + "; level=" + level + "; classMajor=" + major + "; languageFeatures=" + features
                + "; ASM maxClassMajor=" + ASM.getMaxSupportedClassVersionMajor());
        }
    }
}
