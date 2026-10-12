# Add project specific ProGuard rules here.
-keepattributes *Annotation*
-keepclassmembers class * {
    @org.json.* <methods>;
}
