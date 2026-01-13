package com.diveops.chat.api

import retrofit2.Response
import retrofit2.http.*

// Request/Response DTOs
data class LoginRequest(
    val email: String,
    val password: String
)

data class LoginResponse(
    val token: String,
    val user: UserInfo
)

data class UserInfo(
    val id: Int,
    val email: String,
    val first_name: String,
    val last_name: String
)

data class FCMRegisterRequest(
    val registration_id: String,
    val platform: String = "android",
    val device_id: String = "",
    val device_name: String = "",
    val app_version: String = ""
)

data class FCMRegisterResponse(
    val status: String,
    val device_id: String
)

data class ConversationsResponse(
    val conversations: List<ConversationItem>
)

data class ConversationItem(
    val id: String,
    val person_id: String,
    val name: String,
    val email: String,
    val initials: String,
    val last_message: String,
    val last_message_time: String?,
    val needs_reply: Boolean,
    val unread_count: Int,
    val status: String
)

data class MessagesResponse(
    val messages: List<MessageItem>
)

data class MessageItem(
    val id: String,
    val body: String,
    val direction: String,
    val status: String,
    val created_at: String,
    val sender_name: String
)

data class SendMessageRequest(
    val message: String
)

data class SendMessageResponse(
    val status: String,
    val message_id: String
)

data class ErrorResponse(
    val error: String
)

interface ApiService {

    @POST("api/mobile/login/")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @POST("api/mobile/fcm/register/")
    suspend fun registerFCMDevice(
        @Header("Authorization") token: String,
        @Body request: FCMRegisterRequest
    ): Response<FCMRegisterResponse>

    @POST("api/mobile/fcm/unregister/")
    suspend fun unregisterFCMDevice(
        @Header("Authorization") token: String,
        @Body request: FCMRegisterRequest
    ): Response<FCMRegisterResponse>

    @GET("api/mobile/conversations/")
    suspend fun getConversations(
        @Header("Authorization") token: String
    ): Response<ConversationsResponse>

    @GET("api/mobile/conversations/{conversation_id}/messages/")
    suspend fun getMessages(
        @Header("Authorization") token: String,
        @Path("conversation_id") conversationId: String
    ): Response<MessagesResponse>

    @POST("api/mobile/conversations/{conversation_id}/send/")
    suspend fun sendMessage(
        @Header("Authorization") token: String,
        @Path("conversation_id") conversationId: String,
        @Body request: SendMessageRequest
    ): Response<SendMessageResponse>
}
