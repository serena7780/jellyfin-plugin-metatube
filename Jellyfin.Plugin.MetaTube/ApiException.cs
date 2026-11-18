namespace Jellyfin.Plugin.MetaTube;

/// <summary>
/// Exception thrown when the MetaTube backend returns an error response.
/// </summary>
/// <remarks>
/// The error code and message reported by the backend are preserved so that
/// failures can be diagnosed from the Jellyfin log alone.
/// </remarks>
public class ApiException : Exception
{
    public ApiException(int code, string message) : base($"API request error: {code} ({message})")
    {
        Code = code;
    }

    public ApiException(string message) : base(message)
    {
    }

    public ApiException(string message, Exception innerException) : base(message, innerException)
    {
    }

    /// <summary>
    /// Gets the error code reported by the backend.
    /// </summary>
    public int Code { get; } = 0;
}

/// <summary>
/// Exception thrown when the backend cannot find any matching result.
/// </summary>
/// <remarks>
/// This is a normal outcome rather than a failure: the keyword simply does not
/// match anything in the backend. It is reported separately so that it can be
/// logged as a warning instead of an error.
/// </remarks>
public class ApiNotFoundException : ApiException
{
    public ApiNotFoundException(int code, string message) : base(code, message)
    {
    }
}
