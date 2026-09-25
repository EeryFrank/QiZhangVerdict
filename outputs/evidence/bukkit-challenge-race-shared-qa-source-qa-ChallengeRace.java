// SPDX-License-Identifier: GPL-3.0-only
package qa;
import java.nio.charset.StandardCharsets;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerRegisterChannelEvent;
import org.bukkit.plugin.java.JavaPlugin;

/** QA timing only: no reflection, replacement guard classes, or synthetic Bukkit events. */
public final class ChallengeRace extends JavaPlugin implements Listener {
    private static final String CONTROL = "qzqa:control";
    private long tick, joinedTick;
    private Player owner;
    private boolean reloaded, slow;
    public void onEnable() {
        getServer().getMessenger().registerOutgoingPluginChannel(this, CONTROL);
        getServer().getPluginManager().registerEvents(this, this);
        getServer().getScheduler().runTaskTimer(this, () -> tick++, 1L, 1L);
        getLogger().info("QA_READY no guard reflection or policy edits; one synthetic player only");
    }
    @EventHandler(priority = EventPriority.MONITOR)
    public void joined(PlayerJoinEvent event) {
        if (!event.getPlayer().getName().equals("QVRace")) return;
        if (owner != null) throw new IllegalStateException("Fixture permits only one join");
        owner = event.getPlayer(); joinedTick = tick;
        slow = Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "tick rate 1");
        getLogger().info("QA_JOIN tick=" + tick + " slowCommand=" + slow);
        getServer().getScheduler().runTaskLater(this, () -> {
            boolean same = owner != null && Bukkit.getPlayer(owner.getUniqueId()) == owner && owner.isOnline();
            String marker = same && reloaded && slow ? "CHECKPOINT" : "TIMING_NOT_ESTABLISHED";
            if (same) control(marker);
            getLogger().info("QA_CHECKPOINT tick=" + tick + " joinTick=" + joinedTick + " reloaded=" + reloaded);
            restoreTicks();
        }, 4L);
    }
    @EventHandler(priority = EventPriority.MONITOR)
    public void registered(PlayerRegisterChannelEvent event) {
        if (event.getPlayer() != owner || !event.getChannel().equals("qzguard:main") || reloaded) return;
        // The fixture channel is registered first by the client. Guard NORMAL runs before this MONITOR.
        if (!owner.getListeningPluginChannels().contains(CONTROL) || tick - joinedTick >= 2L || !slow) {
            control("TIMING_NOT_ESTABLISHED");
            getLogger().warning("QA_TIMING_NOT_ESTABLISHED registerTick=" + tick + " joinTick=" + joinedTick);
            return;
        }
        control("BEFORE_RELOAD");
        boolean dispatched = Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "qzverdict reload");
        control("AFTER_RELOAD");
        reloaded = dispatched;
        getLogger().info("QA_RELOADED registerTick=" + tick + " joinTick=" + joinedTick + " command=" + dispatched);
    }
    private void control(String stage) {
        owner.sendPluginMessage(this, CONTROL, (stage + "|" + tick + "|" + joinedTick).getBytes(StandardCharsets.US_ASCII));
    }
    private void restoreTicks() {
        if (slow) { Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "tick rate 20"); slow = false; }
    }
    public void onDisable() { restoreTicks(); }
}
