# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.kts.

# Keep data classes used by Retrofit/Gson
-keepclassmembers class com.diveops.chat.api.** { *; }

# Firebase
-keep class com.google.firebase.** { *; }
