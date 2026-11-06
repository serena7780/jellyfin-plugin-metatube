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
    public ApiException(string message) : base(message)
    {
    }

    public ApiException(string message, Exception innerException) : base(message, innerException)
    {
    }
}
