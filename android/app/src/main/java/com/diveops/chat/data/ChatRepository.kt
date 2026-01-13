package com.diveops.chat.data

import com.diveops.chat.api.ApiClient
import com.diveops.chat.api.ConversationItem
import com.diveops.chat.api.MessageItem
import com.diveops.chat.api.SendMessageRequest

class ChatRepository(private val authRepository: AuthRepository) {

    suspend fun getConversations(): Result<List<ConversationItem>> {
        return try {
            val authToken = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.getConversations("Bearer $authToken")

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.conversations)
            } else {
                val errorBody = response.errorBody()?.string() ?: "Failed to load conversations"
                Result.failure(Exception(errorBody))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getMessages(conversationId: String): Result<List<MessageItem>> {
        return try {
            val authToken = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.getMessages(
                token = "Bearer $authToken",
                conversationId = conversationId
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.messages)
            } else {
                val errorBody = response.errorBody()?.string() ?: "Failed to load messages"
                Result.failure(Exception(errorBody))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun sendMessage(conversationId: String, message: String): Result<String> {
        return try {
            val authToken = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.sendMessage(
                token = "Bearer $authToken",
                conversationId = conversationId,
                request = SendMessageRequest(message)
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.message_id)
            } else {
                val errorBody = response.errorBody()?.string() ?: "Failed to send message"
                Result.failure(Exception(errorBody))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
