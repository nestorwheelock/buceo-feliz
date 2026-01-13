package com.diveops.chat

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.diveops.chat.api.ConversationItem
import com.diveops.chat.api.MessageItem
import com.diveops.chat.data.AuthRepository
import com.diveops.chat.data.ChatRepository
import com.diveops.chat.ui.ChatScreen
import com.diveops.chat.ui.ConversationsScreen
import com.diveops.chat.ui.LoginScreen
import com.diveops.chat.ui.theme.DiveOpsChatTheme
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private lateinit var authRepository: AuthRepository
    private lateinit var chatRepository: ChatRepository

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            Log.d(TAG, "Notification permission granted")
        } else {
            Log.d(TAG, "Notification permission denied")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        authRepository = DiveOpsApp.getInstance().authRepository
        chatRepository = ChatRepository(authRepository)

        askNotificationPermission()

        setContent {
            DiveOpsChatTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    AppNavigation()
                }
            }
        }
    }

    @Composable
    private fun AppNavigation() {
        val navController = rememberNavController()
        val coroutineScope = rememberCoroutineScope()

        // Check if user is logged in
        var isLoggedIn by remember { mutableStateOf<Boolean?>(null) }

        LaunchedEffect(Unit) {
            val token = authRepository.authToken.first()
            isLoggedIn = token != null
        }

        // Wait for login state to be determined
        if (isLoggedIn == null) {
            return
        }

        val startDestination = if (isLoggedIn == true) "conversations" else "login"

        NavHost(navController = navController, startDestination = startDestination) {
            composable("login") {
                var isLoading by remember { mutableStateOf(false) }
                var errorMessage by remember { mutableStateOf<String?>(null) }

                LoginScreen(
                    onLogin = { email, password ->
                        coroutineScope.launch {
                            isLoading = true
                            errorMessage = null

                            val result = authRepository.login(email, password)

                            result.fold(
                                onSuccess = {
                                    // Register FCM token after login
                                    registerFCMToken()
                                    navController.navigate("conversations") {
                                        popUpTo("login") { inclusive = true }
                                    }
                                },
                                onFailure = { e ->
                                    errorMessage = e.message ?: getString(R.string.error_login)
                                }
                            )

                            isLoading = false
                        }
                    },
                    isLoading = isLoading,
                    errorMessage = errorMessage
                )
            }

            composable("conversations") {
                var conversations by remember { mutableStateOf<List<ConversationItem>>(emptyList()) }
                var isLoading by remember { mutableStateOf(true) }
                var errorMessage by remember { mutableStateOf<String?>(null) }

                fun loadConversations() {
                    coroutineScope.launch {
                        isLoading = true
                        errorMessage = null

                        val result = chatRepository.getConversations()

                        result.fold(
                            onSuccess = { conversations = it },
                            onFailure = { e -> errorMessage = e.message ?: getString(R.string.error_network) }
                        )

                        isLoading = false
                    }
                }

                LaunchedEffect(Unit) {
                    loadConversations()
                }

                ConversationsScreen(
                    conversations = conversations,
                    isLoading = isLoading,
                    errorMessage = errorMessage,
                    onConversationClick = { conversation ->
                        navController.navigate("chat/${conversation.id}/${conversation.name}/${conversation.initials}/${conversation.email}")
                    },
                    onRefresh = { loadConversations() },
                    onLogout = {
                        coroutineScope.launch {
                            // Unregister FCM token before logout
                            unregisterFCMToken()
                            authRepository.logout()
                            navController.navigate("login") {
                                popUpTo("conversations") { inclusive = true }
                            }
                        }
                    }
                )
            }

            composable(
                route = "chat/{conversationId}/{name}/{initials}/{email}",
                arguments = listOf(
                    navArgument("conversationId") { type = NavType.StringType },
                    navArgument("name") { type = NavType.StringType },
                    navArgument("initials") { type = NavType.StringType },
                    navArgument("email") { type = NavType.StringType }
                )
            ) { backStackEntry ->
                val conversationId = backStackEntry.arguments?.getString("conversationId") ?: ""
                val name = backStackEntry.arguments?.getString("name") ?: ""
                val initials = backStackEntry.arguments?.getString("initials") ?: ""
                val email = backStackEntry.arguments?.getString("email") ?: ""

                val conversation = ConversationItem(
                    id = conversationId,
                    person_id = "",
                    name = name,
                    email = email,
                    initials = initials,
                    last_message = "",
                    last_message_time = null,
                    needs_reply = false,
                    unread_count = 0,
                    status = ""
                )

                var messages by remember { mutableStateOf<List<MessageItem>>(emptyList()) }
                var isLoading by remember { mutableStateOf(true) }
                var isSending by remember { mutableStateOf(false) }

                LaunchedEffect(conversationId) {
                    val result = chatRepository.getMessages(conversationId)
                    result.fold(
                        onSuccess = { messages = it },
                        onFailure = { /* Handle error */ }
                    )
                    isLoading = false
                }

                ChatScreen(
                    conversation = conversation,
                    messages = messages,
                    isLoading = isLoading,
                    isSending = isSending,
                    onSendMessage = { messageText ->
                        coroutineScope.launch {
                            isSending = true
                            val result = chatRepository.sendMessage(conversationId, messageText)
                            result.fold(
                                onSuccess = {
                                    // Reload messages
                                    val messagesResult = chatRepository.getMessages(conversationId)
                                    messagesResult.fold(
                                        onSuccess = { messages = it },
                                        onFailure = { /* Handle error */ }
                                    )
                                },
                                onFailure = { /* Handle error */ }
                            )
                            isSending = false
                        }
                    },
                    onBack = { navController.popBackStack() }
                )
            }
        }
    }

    private fun askNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED
            ) {
                requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    private fun registerFCMToken() {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (task.isSuccessful) {
                val token = task.result
                Log.d(TAG, "FCM Token: $token")

                // Register with server
                kotlinx.coroutines.GlobalScope.launch {
                    try {
                        val deviceId = Settings.Secure.getString(
                            contentResolver,
                            Settings.Secure.ANDROID_ID
                        )
                        val deviceName = "${Build.MANUFACTURER} ${Build.MODEL}"

                        authRepository.registerFCMToken(
                            fcmToken = token,
                            deviceId = deviceId,
                            deviceName = deviceName
                        )
                        Log.d(TAG, "FCM token registered with server")
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to register FCM token", e)
                    }
                }
            } else {
                Log.e(TAG, "Failed to get FCM token", task.exception)
            }
        }
    }

    private fun unregisterFCMToken() {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (task.isSuccessful) {
                kotlinx.coroutines.GlobalScope.launch {
                    try {
                        authRepository.unregisterFCMToken(task.result)
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to unregister FCM token", e)
                    }
                }
            }
        }
    }

    companion object {
        private const val TAG = "MainActivity"
    }
}
