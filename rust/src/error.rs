//! Error handling for the application

use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
};

/// Application error type
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("Page not found")]
    NotFound,

    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),

    #[error("Template error: {0}")]
    Template(#[from] askama::Error),

    #[error("Internal error: {0}")]
    Internal(String),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            AppError::NotFound => (StatusCode::NOT_FOUND, "Page not found"),
            AppError::Database(e) => {
                tracing::error!("Database error: {}", e);
                (StatusCode::INTERNAL_SERVER_ERROR, "Database error")
            }
            AppError::Template(e) => {
                tracing::error!("Template error: {}", e);
                (StatusCode::INTERNAL_SERVER_ERROR, "Template error")
            }
            AppError::Internal(msg) => {
                tracing::error!("Internal error: {}", msg);
                (StatusCode::INTERNAL_SERVER_ERROR, "Internal error")
            }
        };

        // Return simple HTML error page
        let html = format!(
            r#"<!DOCTYPE html>
<html>
<head><title>{} - Happy Diving</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
    <h1>{}</h1>
    <p>{}</p>
    <a href="/">Return to homepage</a>
</body>
</html>"#,
            status.as_u16(),
            status.as_u16(),
            message
        );

        (status, axum::response::Html(html)).into_response()
    }
}

pub type Result<T> = std::result::Result<T, AppError>;
